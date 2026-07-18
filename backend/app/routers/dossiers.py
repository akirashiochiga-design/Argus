"""Dossiers sinistres : lecture, déclaration entrante, exécution pas-à-pas."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..audit import tracer
from ..db import get_session
from ..models import Dossier, Police, Run, Workflow
from ..orchestrator import OrchestrationErreur, avancer

router = APIRouter(tags=["dossiers"])


class DeclarationEntrante(BaseModel):
    declaration_texte: str
    police_numero: str
    pieces: list[dict] = []


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


@router.post("/dossiers", status_code=201)
def declarer_sinistre(corps: DeclarationEntrante, session: Session = Depends(get_session)) -> Dossier:
    """Nouvelle déclaration (texte libre FR/darija) — crée un dossier 'reçu'."""
    police = session.exec(select(Police).where(Police.numero == corps.police_numero)).first()
    if not police:
        raise HTTPException(404, f"Police {corps.police_numero} introuvable")
    workflow = session.exec(select(Workflow)).first()
    numero = session.exec(select(Dossier)).all()
    dossier = Dossier(
        ref=f"SIN-2026-{len(numero) + 1:03d}",
        police_id=police.id,
        workflow_id=workflow.id if workflow else None,
        declaration_texte=corps.declaration_texte,
        pieces=corps.pieces,
    )
    session.add(dossier)
    session.flush()
    tracer(session, acteur="humain:declarant", acteur_type="humain", type="creation_dossier",
           objet=f"dossier:{dossier.ref}", apres={"police": police.numero, "etat": "recu"})
    session.commit()
    session.refresh(dossier)
    return dossier


@router.post("/dossiers/{dossier_id}/executer")
def executer_etape(dossier_id: int, session: Session = Depends(get_session)) -> dict:
    """Avance le dossier d'UNE étape. Le frontend enchaîne les appels (animation).

    Réponses : etape_executee | porte_humaine (pipeline suspendu) | termine.
    """
    dossier = session.get(Dossier, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")
    try:
        return avancer(session, dossier)
    except OrchestrationErreur as e:
        raise HTTPException(e.code, e.detail)
