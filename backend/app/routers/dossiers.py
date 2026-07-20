"""Dossiers sinistres : lecture, déclaration entrante, exécution pas-à-pas."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..audit import tracer
from ..db import get_session
from ..models import Dossier, Police, Run, Workflow
from ..orchestrator import OrchestrationErreur, avancer, reculer
from ..workflow_service import TraitementInvalide, traitement_actif, valider_etapes

router = APIRouter(tags=["dossiers"])


class DeclarationEntrante(BaseModel):
    declaration_texte: str
    police_numero: str
    pieces: list[dict] = []
    branche: str = "auto"


class ChoixTraitement(BaseModel):
    workflow_id: int


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
    workflow = traitement_actif(session, corps.branche)
    numero = session.exec(select(Dossier)).all()
    prefixe = "HAB-SIN-2026-" if corps.branche == "habitation" else "SIN-2026-"
    dossier = Dossier(
        ref=f"{prefixe}{len(numero) + 1:03d}",
        branche=corps.branche,
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


@router.patch("/dossiers/{dossier_id}/traitement")
def choisir_traitement(
    dossier_id: int,
    corps: ChoixTraitement,
    session: Session = Depends(get_session),
) -> Dossier:
    dossier = session.get(Dossier, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")
    if dossier.etape_courante > 0 or dossier.etat != "recu":
        raise HTTPException(409, "Le traitement ne peut plus être changé après son lancement")
    workflow = session.get(Workflow, corps.workflow_id)
    if not workflow or workflow.statut != "live":
        raise HTTPException(404, "Traitement indisponible")
    try:
        valider_etapes(session, [etape["agent_id"] for etape in workflow.etapes])
    except TraitementInvalide as e:
        raise HTTPException(422, str(e)) from e
    avant = dossier.workflow_id
    dossier.workflow_id = workflow.id
    session.add(dossier)
    tracer(
        session,
        acteur="humain:responsable_sinistres",
        acteur_type="humain",
        type="affectation_workflow",
        objet=f"dossier:{dossier.ref}",
        avant={"workflow_id": avant},
        apres={"workflow_id": workflow.id, "nom": workflow.nom},
    )
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


@router.post("/dossiers/{dossier_id}/reculer")
def reculer_etape(dossier_id: int, session: Session = Depends(get_session)) -> dict:
    """Annule la dernière étape (retour arrière). Rejoue proprement l'état."""
    dossier = session.get(Dossier, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")
    try:
        return reculer(session, dossier)
    except OrchestrationErreur as e:
        raise HTTPException(e.code, e.detail)


@router.post("/dossiers/{dossier_id}/rejouer")
def rejouer(dossier_id: int, session: Session = Depends(get_session)) -> dict:
    """Remet un dossier à l'état initial (reçu, étape 0) — rejeu complet en démo."""
    dossier = session.get(Dossier, dossier_id)
    if not dossier:
        raise HTTPException(404, "Dossier introuvable")
    # On recule jusqu'au début
    while True:
        try:
            reculer(session, dossier)
        except OrchestrationErreur:
            break
    return {"resultat": "rejoue", "dossier": dossier.model_dump()}
