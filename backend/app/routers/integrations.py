"""API du connecteur fonctionnel vers la base assurance externe."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..connectors.insurance_sqlite import (
    ConnexionAssuranceInvalide,
    apercu,
    synchroniser,
    tester_connexion,
)
from ..audit import tracer
from ..db import get_session
from ..models import EvenementAudit, IntegrationConnexion


router = APIRouter(prefix="/integrations", tags=["integrations"])


def _erreur_connexion(erreur: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(erreur))


@router.get("/database/statut")
def statut_database(session: Session = Depends(get_session)) -> dict:
    try:
        info = tester_connexion()
    except ConnexionAssuranceInvalide as e:
        raise _erreur_connexion(e) from e
    derniere = session.exec(
        select(EvenementAudit)
        .where(EvenementAudit.type == "synchronisation_donnees")
        .order_by(EvenementAudit.horodatage.desc())
    ).first()
    connexion = session.exec(
        select(IntegrationConnexion).where(
            IntegrationConnexion.identifiant == "insurance_core"
        )
    ).first()
    return {
        **info,
        "statut": "connecte" if connexion else "non_connecte",
        "connecte_le": connexion.connecte_le if connexion else None,
        "derniere_synchronisation": derniere.apres if derniere else None,
    }


@router.post("/database/connecter")
def connecter_database(session: Session = Depends(get_session)) -> dict:
    try:
        info = tester_connexion()
    except ConnexionAssuranceInvalide as e:
        raise _erreur_connexion(e) from e
    connexion = session.exec(
        select(IntegrationConnexion).where(
            IntegrationConnexion.identifiant == "insurance_core"
        )
    ).first()
    if not connexion:
        connexion = IntegrationConnexion(identifiant="insurance_core")
        session.add(connexion)
        session.flush()
        tracer(
            session,
            acteur="humain:responsable_sinistres",
            acteur_type="humain",
            type="connexion_systeme",
            objet="integration:insurance_core",
            apres={"source": info["source"], "organisation": info["organisation"]},
            motif="Connexion validée après contrôle du schéma source",
        )
        session.commit()
        session.refresh(connexion)
    return {**info, "statut": "connecte", "connecte_le": connexion.connecte_le}


@router.post("/database/test")
def test_database() -> dict:
    try:
        return tester_connexion()
    except ConnexionAssuranceInvalide as e:
        raise _erreur_connexion(e) from e


@router.get("/database/apercu")
def apercu_database() -> dict:
    try:
        return apercu()
    except ConnexionAssuranceInvalide as e:
        raise _erreur_connexion(e) from e


@router.post("/database/synchroniser")
def synchroniser_database(session: Session = Depends(get_session)) -> dict:
    connexion = session.exec(
        select(IntegrationConnexion).where(
            IntegrationConnexion.identifiant == "insurance_core"
        )
    ).first()
    if not connexion:
        raise HTTPException(409, "Connectez d'abord la base assurance à Argus")
    try:
        return synchroniser(session)
    except ConnexionAssuranceInvalide as e:
        session.rollback()
        raise _erreur_connexion(e) from e
