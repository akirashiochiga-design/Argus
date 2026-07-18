"""Studio : templates, création d'agents, publication, branchement au pipeline."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from .. import llm
from ..audit import tracer
from ..db import get_session
from ..models import Agent, Template, Workflow

router = APIRouter(tags=["studio"])

# Catégories que le studio autorise pour un agent personnalisé.
# Les catégories "argent" (garanties, indemnite) et la porte (hitl) NE sont
# PAS proposées : on ne laisse pas créer par prompt un agent qui décide d'un
# montant ou contourne la validation humaine — c'est la gouvernance du produit.
CATEGORIES_PERSONNALISEES = {
    "fnol": "Compréhension d'une déclaration (texte)",
    "extraction": "Lecture de documents (OCR / vision)",
    "vision": "Analyse d'images (gravité, dégâts)",
    "courrier": "Rédaction d'un message à l'assuré",
    "assistant": "Assistant métier (usage libre, hors pipeline)",
}


class CreationAgent(BaseModel):
    nom: str
    template_id: int
    instructions: Optional[str] = None
    seuils: dict = {}
    garde_fous: dict = {}


class ModificationAgent(BaseModel):
    instructions: Optional[str] = None
    seuils: Optional[dict] = None
    garde_fous: Optional[dict] = None


@router.get("/templates")
def lister_templates(session: Session = Depends(get_session)) -> list[Template]:
    return session.exec(select(Template)).all()


@router.get("/agents")
def lister_agents(session: Session = Depends(get_session)) -> list[Agent]:
    return session.exec(select(Agent)).all()


@router.post("/agents", status_code=201)
def creer_agent(corps: CreationAgent, session: Session = Depends(get_session)) -> Agent:
    template = session.get(Template, corps.template_id)
    if not template:
        raise HTTPException(404, "Template introuvable")
    # Les garde-fous du template sont TOUJOURS repris — non désactivables depuis le studio
    agent = Agent(
        nom=corps.nom,
        categorie=template.categorie,
        template_id=template.id,
        instructions=corps.instructions or template.instructions_defaut,
        seuils=corps.seuils,
        garde_fous={**template.garde_fous_defaut, **corps.garde_fous},
        statut="draft",
    )
    session.add(agent)
    session.flush()  # obtient agent.id sans expirer l'instance
    tracer(session, "humain:superviseur", "humain", "creation_agent", f"agent:{agent.id}",
           apres={"nom": agent.nom, "template": template.nom, "statut": "draft"})
    session.commit()
    session.refresh(agent)
    return agent


@router.post("/agents/{agent_id}/publier")
def publier_agent(agent_id: int, session: Session = Depends(get_session)) -> Agent:
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent introuvable")
    avant = agent.statut
    agent.statut = "live"
    tracer(session, "humain:superviseur", "humain", "publication_agent", f"agent:{agent.id}",
           avant={"statut": avant}, apres={"statut": "live", "version": agent.version})
    session.commit()
    session.refresh(agent)
    return agent


@router.patch("/agents/{agent_id}")
def modifier_agent(agent_id: int, corps: ModificationAgent, session: Session = Depends(get_session)) -> Agent:
    """Modifier instructions/seuils → nouvelle version, tracée dans l'audit."""
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent introuvable")
    avant = {"version": agent.version, "seuils": agent.seuils, "instructions": agent.instructions[:80]}
    if corps.instructions is not None:
        agent.instructions = corps.instructions
    if corps.seuils is not None:
        agent.seuils = corps.seuils
    if corps.garde_fous is not None:
        # les garde-fous non désactivables du template restent
        agent.garde_fous = {**agent.garde_fous, **corps.garde_fous}
    agent.version += 1
    tracer(session, "humain:superviseur", "humain", "modification_agent", f"agent:{agent.id}",
           avant=avant, apres={"version": agent.version, "seuils": agent.seuils})
    session.commit()
    session.refresh(agent)
    return agent


class Affectation(BaseModel):
    agent_id: int


@router.post("/workflows/{workflow_id}/affecter")
def affecter_agent(workflow_id: int, corps: Affectation, session: Session = Depends(get_session)) -> Workflow:
    """Branche un agent (live) dans le pipeline, à l'étape de sa catégorie."""
    workflow = session.get(Workflow, workflow_id)
    agent = session.get(Agent, corps.agent_id)
    if not workflow or not agent:
        raise HTTPException(404, "Workflow ou agent introuvable")
    if agent.statut != "live":
        raise HTTPException(409, "Seul un agent 'live' peut être branché au pipeline")

    import copy

    ancien_id = None
    # deepcopy obligatoire : muter les dicts en place empêcherait SQLAlchemy
    # de détecter le changement de la colonne JSON (pas d'UPDATE émis)
    etapes = copy.deepcopy(workflow.etapes)
    for etape in etapes:
        etape_agent = session.get(Agent, etape["agent_id"])
        if etape_agent and etape_agent.categorie == agent.categorie:
            ancien_id = etape["agent_id"]
            etape["agent_id"] = agent.id
    if ancien_id is None:
        raise HTTPException(409, f"Aucune étape de catégorie '{agent.categorie}' dans ce workflow")

    workflow.etapes = etapes
    tracer(session, "humain:superviseur", "humain", "affectation_workflow", f"workflow:{workflow.id}",
           avant={"agent_id": ancien_id}, apres={"agent_id": agent.id, "categorie": agent.categorie})
    session.commit()
    session.refresh(workflow)
    return workflow


@router.get("/workflows")
def lister_workflows(session: Session = Depends(get_session)) -> list[Workflow]:
    return session.exec(select(Workflow)).all()


# ---------------- Agent personnalisé depuis un prompt libre ----------------

class BriefAgent(BaseModel):
    brief: str  # description courte de l'agent voulu, en langage naturel


class AgentPersonnalise(BaseModel):
    nom: str
    categorie: str
    instructions: str
    seuils: dict = {}


@router.get("/studio/categories")
def categories_personnalisees() -> dict:
    return CATEGORIES_PERSONNALISEES


@router.post("/studio/generer-instructions")
def generer_instructions(corps: BriefAgent) -> dict:
    """Transforme un brief en langage naturel en instructions d'agent complètes.

    Effet 'no-code assisté par IA' : le métier décrit ce qu'il veut, l'IA rédige
    la consigne. Repli déterministe si pas de clé API (la démo ne casse pas).
    """
    system = (
        "Tu es l'assistant du studio Argus, une plateforme d'agents d'IA pour "
        "l'assurance. À partir d'un brief court, rédige les instructions système "
        "d'un agent : rôle, entrées attendues, sorties attendues, ton. 6 à 10 "
        "lignes, en français, concis et opérationnel. Rappelle en dernière ligne "
        "le garde-fou : l'agent ne décide jamais d'un montant ni d'un paiement, "
        "l'humain valide toute décision d'argent. Ne réponds QUE par les instructions."
    )
    try:
        r = llm.generer_texte(system, f"Brief : {corps.brief}", max_tokens=600)
        return {"instructions": r["texte"].strip(), "mode": "llm", "cout": r["cout"]}
    except llm.LLMIndisponible:
        instructions = (
            f"Rôle : {corps.brief.strip().rstrip('.')}.\n"
            "Entrées : les éléments du dossier sinistre pertinents pour cette tâche.\n"
            "Sorties : un résultat structuré, avec un indice de confiance.\n"
            "Ton : factuel, en français, sans jargon.\n"
            "Signale explicitement toute information manquante plutôt que de l'inventer.\n"
            "Garde-fou : cet agent ne décide jamais d'un montant ni d'un paiement ; "
            "toute décision engageant de l'argent est validée par un humain."
        )
        return {"instructions": instructions, "mode": "simulation", "cout": 0.0}


@router.post("/studio/agents-personnalises", status_code=201)
def creer_agent_personnalise(corps: AgentPersonnalise, session: Session = Depends(get_session)) -> Agent:
    """Crée un agent depuis un prompt libre (pas de template). Draft, garde-fous imposés."""
    if corps.categorie not in CATEGORIES_PERSONNALISEES:
        raise HTTPException(400, f"Catégorie non autorisée depuis le studio : {corps.categorie}")
    agent = Agent(
        nom=corps.nom,
        categorie=corps.categorie,
        template_id=None,
        instructions=corps.instructions,
        seuils=corps.seuils,
        # garde-fous non négociables, quelle que soit la consigne saisie
        garde_fous={"pas_de_decision_argent": True, "origine": "prompt_studio"},
        statut="draft",
    )
    session.add(agent)
    session.flush()
    tracer(session, "humain:superviseur", "humain", "creation_agent", f"agent:{agent.id}",
           apres={"nom": agent.nom, "categorie": agent.categorie, "origine": "prompt personnalisé"})
    session.commit()
    session.refresh(agent)
    return agent
