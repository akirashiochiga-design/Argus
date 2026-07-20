"""File d'approbation — le humain-dans-la-boucle.

Rien ne passe à l'état 'réglé' sans une décision enregistrée ici.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..connectors.erp_stub import planifier_ecriture
from ..db import get_session
from ..models import Dossier, Police, Tache
from ..orchestrator import OrchestrationErreur, decider, relancer

router = APIRouter(tags=["approbations"])


class Decision(BaseModel):
    decision: str  # approuver | modifier | refuser | sans_suite
    validateur: str
    montant: Optional[float] = None
    motif: Optional[str] = None


class Relance(BaseModel):
    validateur: str


@router.get("/taches")
def lister_taches(etat: Optional[str] = None, session: Session = Depends(get_session)) -> list[dict]:
    requete = select(Tache).order_by(Tache.id.desc())
    if etat:
        requete = requete.where(Tache.etat == etat)
    taches = session.exec(requete).all()
    out = []
    for t in taches:
        dossier = session.get(Dossier, t.dossier_id)
        police = session.get(Police, dossier.police_id) if dossier else None
        pieces = dossier.pieces if dossier else []
        piece_chiffree = next(
            (piece for piece in reversed(pieces) if piece.get("type") in ("facture", "devis")),
            None,
        )
        out.append({
            **t.model_dump(),
            "dossier_ref": dossier.ref if dossier else None,
            "assure_nom": police.assure_nom if police else None,
            "police_numero": police.numero if police else None,
            "pieces": pieces,
            "piece_chiffree_recue": piece_chiffree is not None,
            "piece_chiffree": piece_chiffree,
        })
    return out


@router.post("/taches/{tache_id}/decider")
def decider_tache(tache_id: int, corps: Decision, session: Session = Depends(get_session)) -> dict:
    tache = session.get(Tache, tache_id)
    if not tache:
        raise HTTPException(404, "Tâche introuvable")
    try:
        resultat = decider(
            session,
            tache,
            corps.decision,
            corps.validateur,
            montant=corps.montant,
            motif=corps.motif,
        )
        if corps.decision in ("approuver", "modifier"):
            ecriture = planifier_ecriture(
                session,
                session.get(Dossier, tache.dossier_id),
                corps.validateur,
            )
            resultat["ecriture_erp"] = ecriture.model_dump() if ecriture else None
        return resultat
    except OrchestrationErreur as e:
        raise HTTPException(e.code, e.detail)


@router.post("/taches/{tache_id}/relancer")
def relancer_tache(tache_id: int, corps: Relance, session: Session = Depends(get_session)) -> dict:
    """Envoie une relance à l'assuré sur une tâche 'pièce manquante' (courrier généré par LLM)."""
    tache = session.get(Tache, tache_id)
    if not tache:
        raise HTTPException(404, "Tâche introuvable")
    try:
        return relancer(session, tache, corps.validateur)
    except OrchestrationErreur as e:
        raise HTTPException(e.code, e.detail)
