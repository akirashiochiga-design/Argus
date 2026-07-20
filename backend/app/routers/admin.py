"""Réinitialisation des données de référence."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

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
    "bibliotheque": "Sinistres / 2026",
    "dossiers": [
        {
            "ref": "HAB-SIN-2026-0001",
            "branche": "habitation",
            "police_numero": "HAB-2026-0088",
            "assure": "Sami Karoui",
            "declaration": (
                "Un feu s'est déclaré ce matin sur le plan de travail de la cuisine, sans "
                "doute causé par un appareil électrique resté branché. Les dégâts touchent "
                "le mobilier, l'installation électrique et les murs. Un devis de réparation "
                "et une photo des dégâts sont joints."
            ),
            "type_sinistre": "incendie",
            "statut_sharepoint": "a_traiter",
            "documents": [
                {
                    "type": "devis",
                    "chemin": "docs/samples/devis-incendie.jpg",
                    "nom_source": "devis-reparation-hab0001.jpg",
                    "montant": 3200,
                },
                {
                    "type": "photo_degats",
                    "chemin": "docs/samples/degats-incendie.jpg",
                    "nom_source": "photo-degats-cuisine-hab0001.jpg",
                },
            ],
        },
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
    """Remet Norix à l'état de démo : seed vide, SharePoint reset, aucune connexion active.

    Pipeline vide — les dossiers arrivent via déclaration, extraction SharePoint,
    ou sync CoreSinistre. Toutes les intégrations restent à reconnecter manuellement.
    """
    try:
        seed()
    except Exception as e:
        raise HTTPException(500, f"Échec du seed : {e}") from e

    sharepoint = _restaurer_sharepoint()
    erreurs: list[str] = []

    with Session(engine) as session:
        nb_dossiers = len(session.exec(select(Dossier)).all())
        nb_connexions = len(session.exec(select(IntegrationConnexion)).all())

    # Vérifie seulement la dispo technique — ne reconnecte rien.
    coresinistre_dispo = False
    try:
        info = tester_connexion()
        coresinistre_dispo = bool(info)
    except ConnexionAssuranceInvalide as e:
        erreurs.append(f"CoreSinistre indisponible : {e}")

    return {
        "statut": "ok",
        "message": "Données restaurées — pipeline vide, toutes les intégrations déconnectées",
        "dossiers": nb_dossiers,
        "connexions": nb_connexions,
        "sharepoint": sharepoint,
        "coresinistre": {
            "statut": "non_connecte",
            "disponible": coresinistre_dispo,
            "sinistres_importes": False,
        },
        "erreurs": erreurs,
    }
