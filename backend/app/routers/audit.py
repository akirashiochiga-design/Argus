"""Journal d'audit — lecture seule, la table est append-only."""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models import EvenementAudit

router = APIRouter(tags=["audit"])


@router.get("/audit")
def lire_audit(
    objet: Optional[str] = None,
    acteur_type: Optional[str] = None,
    limit: int = 100,
    session: Session = Depends(get_session),
) -> list[EvenementAudit]:
    requete = select(EvenementAudit).order_by(EvenementAudit.id.desc()).limit(min(limit, 500))
    if objet:
        requete = requete.where(EvenementAudit.objet.contains(objet))
    if acteur_type:
        requete = requete.where(EvenementAudit.acteur_type == acteur_type)
    return session.exec(requete).all()
