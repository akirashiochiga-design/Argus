"""Lecture des dossiers sinistres. L'exécution (/executer) arrive à l'étape 2."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Dossier, Police, Run, Workflow

router = APIRouter(tags=["dossiers"])


@router.get("/dossiers")
def lister_dossiers(session: Session = Depends(get_session)) -> list[dict]:
    dossiers = session.exec(select(Dossier)).all()
    out = []
    for d in dossiers:
        police = session.get(Police, d.police_id)
        out.append(
            {
                **d.model_dump(),
                "assure_nom": police.assure_nom if police else None,
                "formule": police.formule if police else None,
            }
        )
    return out


@router.get("/dossiers/{dossier_id}")
def lire_dossier(dossier_id: int, session: Session = Depends(get_session)) -> dict:
    """Tout ce qu'il faut à la vue Pipeline : dossier + police + étapes + runs."""
    dossier = session.get(Dossier, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")
    police = session.get(Police, dossier.police_id)
    workflow = session.get(Workflow, dossier.workflow_id) if dossier.workflow_id else None
    runs = session.exec(
        select(Run).where(Run.dossier_id == dossier_id).order_by(Run.id)
    ).all()
    return {
        "dossier": dossier,
        "police": police,
        "workflow": workflow,
        "runs": runs,
    }
