"""API du connecteur fonctionnel vers la base assurance externe."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..connectors import catalogue, obtenir
from ..connectors import documents_local as sharepoint
from ..connectors.insurance_sqlite import (
    ConnexionAssuranceInvalide,
    apercu,
    creer_police,
    creer_sinistre,
    inventaire,
    synchroniser,
    tester_connexion,
)
from ..audit import tracer
from ..db import get_session
from ..models import Dossier, EcritureERP, EvenementAudit, IntegrationConnexion


router = APIRouter(prefix="/integrations", tags=["integrations"])


class PoliceSourceIn(BaseModel):
    assure_nom: str = Field(min_length=2, max_length=120)
    marque: str = Field(min_length=1, max_length=60)
    modele: str = Field(min_length=1, max_length=60)
    immatriculation: str = Field(min_length=3, max_length=20)
    formule: str = "tous_risques"
    annee: int = 2023
    numero: str | None = None
    ville: str | None = None
    telephone: str | None = None


class SinistreSourceIn(BaseModel):
    police_numero: str = Field(min_length=3, max_length=40)
    declaration: str = Field(min_length=10, max_length=2000)
    type_sinistre: str = "collision"
    montant_estime: float | None = None
    reference: str | None = None


class DocumentSharePointIn(BaseModel):
    dossier_ref: str = Field(min_length=3, max_length=40)
    type: str = "photo_expertise"
    chemin: str = "docs/samples/degats-3.jpg"
    nom_source: str | None = None
    montant: float | None = None
    police_numero: str | None = None
    assure: str | None = None
    declaration: str | None = None


class RetourSharePointIn(BaseModel):
    dossier_id: int
    validateur: str = "superviseur"


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
        "protocole": "MCP",
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
            apres={"source": info["source"], "organisation": info["organisation"], "protocole": "MCP"},
            motif="Connexion validée après contrôle du schéma source via MCP",
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
        raise HTTPException(409, "Connectez d'abord la base assurance à Norix")
    try:
        return synchroniser(session)
    except ConnexionAssuranceInvalide as e:
        session.rollback()
        raise _erreur_connexion(e) from e


@router.get("/database/inventaire")
def inventaire_database() -> dict:
    try:
        return inventaire()
    except ConnexionAssuranceInvalide as e:
        raise _erreur_connexion(e) from e


@router.post("/database/polices")
def ajouter_police_source(corps: PoliceSourceIn) -> dict:
    try:
        return creer_police(corps.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except ConnexionAssuranceInvalide as e:
        raise _erreur_connexion(e) from e


@router.post("/database/sinistres")
def ajouter_sinistre_source(corps: SinistreSourceIn) -> dict:
    try:
        return creer_sinistre(corps.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except ConnexionAssuranceInvalide as e:
        raise _erreur_connexion(e) from e


@router.get("/sharepoint/documents")
def lister_documents_sharepoint() -> dict:
    return sharepoint.lister_documents()


@router.get("/sharepoint/bibliotheque")
def lister_bibliotheque_sharepoint() -> dict:
    return sharepoint.lister_bibliotheque()


@router.post("/sharepoint/documents")
def ajouter_document_sharepoint(corps: DocumentSharePointIn) -> dict:
    try:
        return sharepoint.ajouter_document(corps.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


@router.post("/sharepoint/retours")
def deposer_retour_sharepoint(
    corps: RetourSharePointIn,
    session: Session = Depends(get_session),
) -> dict:
    try:
        return sharepoint.deposer_retour(session, corps.dossier_id, corps.validateur)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e


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
                "protocole": getattr(connecteur, "protocole", info.get("protocole")),
                "simulation": info.get("simulation", False),
            },
            motif="Test réussi et adaptateur activé depuis le registre Norix",
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
        raise HTTPException(409, "Connectez d'abord cet adaptateur à Norix")
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
