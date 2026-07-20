"""Studio : templates, création d'agents, publication, branchement au pipeline."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from .. import llm
from ..agents.tools import noms_pour
from ..audit import tracer
from ..db import get_session
from ..models import Agent, Dossier, Template, Workflow
from ..workflow_service import TraitementInvalide, valider_etapes

router = APIRouter(tags=["studio"])

# Catégories que le studio autorise pour un agent personnalisé.
# Les catégories "argent" (garanties, indemnite) et la porte (hitl) NE sont
# PAS proposées : on ne laisse pas créer par prompt un agent qui décide d'un
# montant ou contourne la validation humaine — c'est la gouvernance du produit.
CATEGORIES_PERSONNALISEES = {
    "fnol": "Qualification de déclaration",
    "extraction": "Extraction documentaire",
    "vision": "Analyse des dégâts",
    "courrier": "Rédaction d'un message à l'assuré",
    "assistant": "Assistant métier (hors parcours sinistre)",
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
        raise HTTPException(404, "Module introuvable")
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
        raise HTTPException(404, "Module introuvable")
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


class TraitementEntrant(BaseModel):
    nom: str
    description: str = ""
    agent_ids: list[int]


class EtapesTraitement(BaseModel):
    agent_ids: list[int]


def _etapes_valides(session: Session, agent_ids: list[int]) -> list[dict]:
    try:
        return valider_etapes(session, agent_ids)
    except TraitementInvalide as e:
        raise HTTPException(422, str(e)) from e


@router.post("/workflows", status_code=201)
def creer_workflow(
    corps: TraitementEntrant,
    session: Session = Depends(get_session),
) -> Workflow:
    nom = corps.nom.strip()
    if len(nom) < 3:
        raise HTTPException(422, "Le nom du traitement doit contenir au moins 3 caractères")
    if session.exec(select(Workflow).where(Workflow.nom == nom)).first():
        raise HTTPException(409, "Un traitement porte déjà ce nom")
    etapes = _etapes_valides(session, corps.agent_ids)
    workflow = Workflow(
        nom=nom,
        description=corps.description.strip(),
        statut="live",
        est_defaut=False,
        etapes=etapes,
    )
    session.add(workflow)
    session.flush()
    tracer(
        session,
        "humain:responsable_sinistres",
        "humain",
        "creation_workflow",
        f"workflow:{workflow.id}",
        apres={"nom": workflow.nom, "nb_etapes": len(etapes)},
    )
    session.commit()
    session.refresh(workflow)
    return workflow


@router.patch("/workflows/{workflow_id}/etapes")
def modifier_etapes_workflow(
    workflow_id: int,
    corps: EtapesTraitement,
    session: Session = Depends(get_session),
) -> Workflow:
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(404, "Traitement introuvable")
    dossiers_commences = session.exec(
        select(Dossier).where(
            Dossier.workflow_id == workflow.id,
            Dossier.etape_courante > 0,
        )
    ).first()
    if dossiers_commences:
        raise HTTPException(
            409,
            "Ce traitement est déjà utilisé par des dossiers en cours et ne peut plus être réordonné",
        )
    etapes = _etapes_valides(session, corps.agent_ids)
    avant = {"agent_ids": [etape["agent_id"] for etape in workflow.etapes]}
    workflow.etapes = etapes
    session.add(workflow)
    tracer(
        session,
        "humain:responsable_sinistres",
        "humain",
        "modification_workflow",
        f"workflow:{workflow.id}",
        avant=avant,
        apres={"agent_ids": corps.agent_ids},
    )
    session.commit()
    session.refresh(workflow)
    return workflow


@router.post("/workflows/{workflow_id}/activer")
def activer_workflow(
    workflow_id: int,
    session: Session = Depends(get_session),
) -> Workflow:
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(404, "Traitement introuvable")
    _etapes_valides(session, [etape["agent_id"] for etape in workflow.etapes])
    for autre in session.exec(select(Workflow)).all():
        autre.est_defaut = autre.id == workflow.id
        session.add(autre)
    tracer(
        session,
        "humain:responsable_sinistres",
        "humain",
        "activation_workflow",
        f"workflow:{workflow.id}",
        apres={"nom": workflow.nom, "est_defaut": True},
    )
    session.commit()
    session.refresh(workflow)
    return workflow


@router.post("/workflows/{workflow_id}/ajouter-etape")
def ajouter_etape(workflow_id: int, corps: Affectation, session: Session = Depends(get_session)) -> Workflow:
    """Ajoute un agent (live) comme NOUVELLE étape du pipeline.

    Il s'AJOUTE — il ne remplace jamais un agent existant. Inséré juste après
    la première étape de même catégorie (le point d'insertion le plus lisible :
    "un contrôle de plus, au même endroit du parcours"), ou avant la porte
    humaine si aucune étape de cette catégorie n'existe déjà.

    Les dossiers déjà en cours d'exécution sur ce workflow ont leur curseur
    (`etape_courante`) décalé d'un cran s'il pointait au-delà du point
    d'insertion, pour ne sauter ni rejouer aucune étape.
    """
    import copy

    workflow = session.get(Workflow, workflow_id)
    agent = session.get(Agent, corps.agent_id)
    if not workflow or not agent:
        raise HTTPException(404, "Parcours ou module introuvable")
    if agent.statut != "live":
        raise HTTPException(409, "Seul un module publié peut être ajouté au parcours")
    if any(e["agent_id"] == agent.id for e in workflow.etapes):
        raise HTTPException(409, "Ce module est déjà présent dans le parcours")

    # deepcopy obligatoire : muter les dicts en place empêcherait SQLAlchemy
    # de détecter le changement de la colonne JSON (pas d'UPDATE émis)
    etapes = copy.deepcopy(workflow.etapes)
    position = None
    for i, etape in enumerate(etapes):
        if etape["type"] != "agent":
            continue
        etape_agent = session.get(Agent, etape["agent_id"])
        if etape_agent and etape_agent.categorie == agent.categorie:
            position = i + 1
            break
    if position is None:  # pas d'étape de cette catégorie : insertion avant la porte humaine
        position = next((i for i, e in enumerate(etapes) if e["type"] == "porte_humaine"), len(etapes))

    etapes.insert(position, {"agent_id": agent.id, "type": "agent"})
    etapes = _etapes_valides(session, [etape["agent_id"] for etape in etapes])
    workflow.etapes = etapes

    for dossier in session.exec(select(Dossier).where(Dossier.workflow_id == workflow.id)).all():
        if dossier.etape_courante >= position:
            dossier.etape_courante += 1

    tracer(session, "humain:superviseur", "humain", "ajout_etape_workflow", f"workflow:{workflow.id}",
           avant={"nb_etapes": len(etapes) - 1},
           apres={"nb_etapes": len(etapes), "agent_id": agent.id, "position": position})
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
        "À partir d'un besoin métier court, rédige les instructions opérationnelles "
        "du module : rôle, entrées attendues, sorties attendues et ton. 6 à 10 "
        "lignes, en français, concis et opérationnel. Rappelle en dernière ligne "
        "la règle : le module ne décide jamais d'un montant ni d'un paiement, "
        "un gestionnaire valide toute décision financière. Ne réponds QUE par les instructions."
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
            "Règle : ce module ne décide jamais d'un montant ni d'un paiement ; "
            "toute décision financière est validée par un gestionnaire."
        )
        return {"instructions": instructions, "cout": 0.0}


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
        garde_fous={
            "pas_de_decision_argent": True,
            "origine": "prompt_studio",
            "outils_autorises": noms_pour(corps.categorie),
            "max_iterations_agent": 4,
        },
        statut="draft",
    )
    session.add(agent)
    session.flush()
    tracer(session, "humain:superviseur", "humain", "creation_agent", f"agent:{agent.id}",
           apres={"nom": agent.nom, "categorie": agent.categorie, "origine": "prompt personnalisé"})
    session.commit()
    session.refresh(agent)
    return agent


@router.get("/studio/plateformes-mcp")
def lister_plateformes_mcp() -> list[dict]:
    """Catalogue type console Anthropic : apps connectables aux agents via MCP."""
    from ..connectors import plateformes as apps

    return apps.catalogue()


@router.get("/agents/{agent_id}/connexions")
def lister_connexions_agent(agent_id: int, session: Session = Depends(get_session)) -> dict:
    from ..connectors import plateformes as apps

    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Module introuvable")
    connexions = (agent.garde_fous or {}).get("connexions_mcp") or {}
    catalogue = []
    for plateforme in apps.catalogue():
        active = connexions.get(plateforme["slug"])
        catalogue.append(
            {
                **plateforme,
                "connecte": bool(active),
                "connexion": active,
            }
        )
    return {
        "agent_id": agent.id,
        "agent_nom": agent.nom,
        "protocole": "MCP",
        "plateformes": catalogue,
        "connectees": sum(1 for item in catalogue if item["connecte"]),
    }


@router.post("/agents/{agent_id}/connexions/{slug}/connecter")
def connecter_plateforme(
    agent_id: int,
    slug: str,
    session: Session = Depends(get_session),
) -> dict:
    """Simule OAuth + active le pack de tools MCP sur l'agent."""
    from ..connectors import plateformes as apps

    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Module introuvable")
    try:
        plateforme = apps.obtenir(slug)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    avant = dict((agent.garde_fous or {}).get("connexions_mcp") or {})
    agent.garde_fous = apps.connecter(agent.garde_fous or {}, slug)
    agent.version += 1
    # Force SQLAlchemy à voir le changement JSON
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(agent, "garde_fous")
    connexion = agent.garde_fous["connexions_mcp"][slug]
    tracer(
        session,
        "humain:superviseur",
        "humain",
        "connexion_mcp_plateforme",
        f"agent:{agent.id}",
        avant={"connexions": list(avant.keys())},
        apres={
            "plateforme": slug,
            "nom": plateforme["nom"],
            "compte": connexion["compte"],
            "tools": connexion["tools"],
            "protocole": "MCP",
            "simulation": True,
        },
        motif=f"Connexion MCP à {plateforme['nom']}",
    )
    session.commit()
    session.refresh(agent)
    return {
        "agent_id": agent.id,
        "plateforme": slug,
        "connexion": connexion,
        "version": agent.version,
    }


@router.delete("/agents/{agent_id}/connexions/{slug}")
def deconnecter_plateforme(
    agent_id: int,
    slug: str,
    session: Session = Depends(get_session),
) -> dict:
    from ..connectors import plateformes as apps

    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Module introuvable")
    try:
        plateforme = apps.obtenir(slug)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    avant = dict((agent.garde_fous or {}).get("connexions_mcp") or {})
    if slug not in avant:
        raise HTTPException(404, f"Aucune connexion active pour {slug}")
    agent.garde_fous = apps.deconnecter(agent.garde_fous or {}, slug)
    agent.version += 1
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(agent, "garde_fous")
    tracer(
        session,
        "humain:superviseur",
        "humain",
        "deconnexion_mcp_plateforme",
        f"agent:{agent.id}",
        avant={"plateforme": slug, "compte": avant[slug].get("compte")},
        apres={"plateforme": slug, "statut": "deconnecte"},
        motif=f"Déconnexion MCP de {plateforme['nom']}",
    )
    session.commit()
    session.refresh(agent)
    return {"agent_id": agent.id, "plateforme": slug, "statut": "deconnecte", "version": agent.version}
