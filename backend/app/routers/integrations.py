"""API du connecteur fonctionnel vers la base assurance externe."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..connectors import catalogue, obtenir
from ..connectors.insurance_sqlite import (
    ConnexionAssuranceInvalide,
    apercu,
    synchroniser,
    tester_connexion,
)
from ..audit import tracer
from ..db import get_session
from ..models import Dossier, EcritureERP, EvenementAudit, IntegrationConnexion


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


@router.get("/connecteurs")
def lister_connecteurs(session: Session = Depends(get_session)) -> list[dict]:
    connexions = {
        connexion.identifiant: connexion
        for connexion in session.exec(select(IntegrationConnexion)).all()
    }
    resultat = []
    for definition in catalogue():
        connecteur = obtenir(definition["identifiant"])
        try:
            test = connecteur.tester()
            disponible = True
        except (FileNotFoundError, ValueError, ConnexionAssuranceInvalide) as e:
            test = {"erreur": str(e)}
            disponible = False
        connexion = connexions.get(definition["identifiant"])
        resultat.append(
            {
                **definition,
                **test,
                "disponible": disponible,
                "statut": "connecte" if connexion else "non_connecte",
                "connecte_le": connexion.connecte_le if connexion else None,
            }
        )
    return resultat


@router.post("/connecteurs/{identifiant}/connecter")
def connecter(
    identifiant: str,
    session: Session = Depends(get_session),
) -> dict:
    try:
        connecteur = obtenir(identifiant)
        info = connecteur.tester()
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except (FileNotFoundError, ValueError, ConnexionAssuranceInvalide) as e:
        raise HTTPException(503, str(e)) from e
    connexion = session.exec(
        select(IntegrationConnexion).where(
            IntegrationConnexion.identifiant == identifiant
        )
    ).first()
    if not connexion:
        connexion = IntegrationConnexion(identifiant=identifiant)
        session.add(connexion)
        session.flush()
        tracer(
            session,
            acteur="humain:responsable_sinistres",
            acteur_type="humain",
            type="connexion_systeme",
            objet=f"integration:{identifiant}",
            apres={
                "nom": connecteur.nom,
                "direction": connecteur.direction,
                "simulation": info.get("simulation", False),
            },
            motif="Test réussi et adaptateur activé depuis le registre Argus",
        )
        session.commit()
        session.refresh(connexion)
    return {**info, "statut": "connecte", "connecte_le": connexion.connecte_le}


@router.post("/connecteurs/{identifiant}/synchroniser")
def synchroniser_connecteur(
    identifiant: str,
    session: Session = Depends(get_session),
) -> dict:
    try:
        connecteur = obtenir(identifiant)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    connexion = session.exec(
        select(IntegrationConnexion).where(
            IntegrationConnexion.identifiant == identifiant
        )
    ).first()
    if not connexion:
        raise HTTPException(409, "Connectez d'abord cet adaptateur à Argus")
    try:
        return connecteur.synchroniser(session)
    except (FileNotFoundError, ValueError, ConnexionAssuranceInvalide) as e:
        session.rollback()
        raise HTTPException(503, str(e)) from e


@router.get("/erp/ecritures")
def lister_ecritures_erp(session: Session = Depends(get_session)) -> list[dict]:
    ecritures = session.exec(select(EcritureERP).order_by(EcritureERP.id.desc())).all()
    resultat = []
    for ecriture in ecritures:
        dossier = session.get(Dossier, ecriture.dossier_id)
        resultat.append(
            {
                **ecriture.model_dump(),
                "dossier_ref": dossier.ref if dossier else None,
            }
        )
    return resultat
