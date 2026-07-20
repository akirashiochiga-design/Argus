"""Réinitialisation des données de référence."""
from fastapi import APIRouter
from sqlmodel import Session

from ..audit import tracer
from ..connectors.insurance_sqlite import ConnexionAssuranceInvalide, synchroniser, tester_connexion
from ..db import engine
from ..models import IntegrationConnexion
from ..seed import seed

router = APIRouter(tags=["admin"])


@router.post("/admin/reseed")
def reseed() -> dict:
    seed()
    synchronisation = None
    with Session(engine) as session:
        try:
            info = tester_connexion()
        except ConnexionAssuranceInvalide:
            info = None
        if info:
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
            try:
                synchronisation = synchroniser(session)
            except ConnexionAssuranceInvalide:
                session.rollback()
    return {
        "statut": "ok",
        "message": "Données restaurées à l'état de référence",
        "synchronisation": synchronisation,
    }
