"""Studio : templates, création d'agents, publication, branchement au pipeline."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..audit import tracer
from ..db import get_session
from ..models import Agent, Template, Workflow

router = APIRouter(tags=["studio"])


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
