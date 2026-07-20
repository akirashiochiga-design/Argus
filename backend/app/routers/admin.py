"""Réinitialisation des données de référence."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from ..audit import tracer
from ..connectors.insurance_sqlite import ConnexionAssuranceInvalide, tester_connexion
from ..db import engine
from ..models import Dossier, IntegrationConnexion
from ..seed import seed

router = APIRouter(tags=["admin"])

RACINE = Path(__file__).resolve().parents[3]
MANIFESTE_SHAREPOINT = RACINE / "docs" / "inbox" / "sharepoint-manifest.json"
MANIFESTE_SHAREPOINT_REF = {
    "source": "SharePoint Sinistres",
    "tenant": "Horizon Assurances",
    "bibliotheque": "Sinistres Auto / 2026",
    "dossiers": [
        {
            "ref": "SP-2026-0142",
            "police_numero": "PA-2024-1183",
            "assure": "Sami Bouazizi",
            "declaration": (
                "Choc matériel au parking Carrefour Lac 2. Pare-chocs avant et "
                "phare gauche endommagés. Constat amiable et photos déposés dans "
                "le dossier SharePoint."
            ),
            "type_sinistre": "collision",
            "statut_sharepoint": "a_traiter",
            "documents": [
                {
                    "type": "constat",
                    "chemin": "docs/samples/constat.jpg",
                    "nom_source": "constat-amiable-0142.jpg",
                },
                {
                    "type": "photo_expertise",
                    "chemin": "docs/samples/degats-1.jpg",
                    "nom_source": "photo-avant-0142.jpg",
                },
                {
                    "type": "facture",
                    "chemin": "docs/samples/facture.jpg",
                    "nom_source": "facture-garage-0142.jpg",
                    "montant": 1850,
                },
            ],
        },
        {
            "ref": "EXT-SIN-2026-1002",
            "police_numero": "PA-2025-0212",
            "assure": "Nour Ben Ammar",
            "declaration": (
                "Collision en sortie de rond-point à Ariana. Aile droite enfoncée. "
                "Pièces déjà présentes dans la bibliothèque SharePoint."
            ),
            "type_sinistre": "collision",
            "statut_sharepoint": "a_traiter",
            "documents": [
                {
                    "type": "constat",
                    "chemin": "docs/samples/constat.jpg",
                    "nom_source": "constat-signe-1002.jpg",
                }
            ],
        },
        {
            "ref": "SIN-2026-004",
            "police_numero": "PA-2024-0967",
            "assure": "Hedi Trabelsi",
            "declaration": (
                "Complément de pièces pour sinistre déjà ouvert dans Norix — "
                "facture de réparation déposée sur SharePoint."
            ),
            "type_sinistre": "collision",
            "statut_sharepoint": "a_traiter",
            "documents": [
                {
                    "type": "facture",
                    "chemin": "docs/samples/facture.jpg",
                    "nom_source": "facture-reparation-004.jpg",
                    "montant": 1650,
                }
            ],
        },
    ],
    "retours": [],
}


def _restaurer_sharepoint() -> dict:
    MANIFESTE_SHAREPOINT.parent.mkdir(parents=True, exist_ok=True)
    MANIFESTE_SHAREPOINT.write_text(
        json.dumps(MANIFESTE_SHAREPOINT_REF, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "dossiers": len(MANIFESTE_SHAREPOINT_REF["dossiers"]),
        "retours": 0,
    }


@router.post("/admin/reseed")
def reseed() -> dict:
    """Remet Norix à l'état de démo : seed vide + SharePoint reset.

    Pipeline vide volontairement — les dossiers arrivent via déclaration,
    extraction SharePoint, ou sync CoreSinistre depuis Intégrations.
    """
    try:
        seed()
    except Exception as e:
        raise HTTPException(500, f"Échec du seed : {e}") from e

    sharepoint = _restaurer_sharepoint()
    erreurs: list[str] = []
    coresinistre = None

    with Session(engine) as session:
        try:
            info = tester_connexion()
        except ConnexionAssuranceInvalide as e:
            info = None
            erreurs.append(f"CoreSinistre indisponible : {e}")

        if info:
            existante = session.exec(
                select(IntegrationConnexion).where(
                    IntegrationConnexion.identifiant == "insurance_core"
                )
            ).first()
            if not existante:
                session.add(IntegrationConnexion(identifiant="insurance_core"))
                session.flush()
                tracer(
                    session,
                    acteur="humain:responsable_sinistres",
                    acteur_type="humain",
                    type="connexion_systeme",
                    objet="integration:insurance_core",
                    apres={
                        "source": info["source"],
                        "organisation": info["organisation"],
                        "protocole": "MCP",
                    },
                    motif="Reconnecté après restauration — import sinistres laissé manuel",
                )
                session.commit()
            coresinistre = {
                "statut": "connecte",
                "source": info["source"],
                "sinistres_importes": False,
            }

        nb_dossiers = len(session.exec(select(Dossier)).all())

    return {
        "statut": "ok",
        "message": "Données restaurées — pipeline vide, prêt pour la démo",
        "dossiers": nb_dossiers,
        "sharepoint": sharepoint,
        "coresinistre": coresinistre,
        "erreurs": erreurs,
    }
