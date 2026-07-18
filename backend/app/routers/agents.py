"""Lecture des templates et agents (le Studio — création — arrive à l'étape 4)."""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models import Agent, Template

router = APIRouter(tags=["studio"])


@router.get("/templates")
def lister_templates(session: Session = Depends(get_session)) -> list[Template]:
    return session.exec(select(Template)).all()


@router.get("/agents")
def lister_agents(session: Session = Depends(get_session)) -> list[Agent]:
    return session.exec(select(Agent)).all()
