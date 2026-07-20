"""Outils en lecture seule accessibles aux agents IA.

Le registre est fermé par défaut : un agent ne peut appeler que les outils
déclarés pour sa catégorie. Aucun outil financier ou mutant n'est exposé.
"""
from typing import Any

from sqlmodel import Session

from ..models import Dossier, Police


class OutilInterdit(Exception):
    """L'agent a demandé un outil absent de sa liste blanche."""


DEFINITIONS = {
    "consulter_police": {
        "name": "consulter_police",
        "description": (
            "Consulter les informations contractuelles et le véhicule assuré liés au dossier. "
            "Outil en lecture seule : il ne prend aucune décision de couverture ou de paiement."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    "inventorier_pieces": {
        "name": "inventorier_pieces",
        "description": (
            "Inventorier les types de pièces jointes et leurs métadonnées utiles, sans lire "
            "ni modifier un montant d'indemnisation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    "consulter_vehicule_assure": {
        "name": "consulter_vehicule_assure",
        "description": (
            "Consulter la marque, le modèle, l'année et l'immatriculation du véhicule assuré "
            "afin d'évaluer si les photos permettent de vérifier son identité."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    "consulter_bien_assure": {
        "name": "consulter_bien_assure",
        "description": (
            "Consulter les caractéristiques du bien assuré (type de bien, adresse, année de "
            "construction) afin de comparer les photos de dégâts aux éléments déclarés."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    "consulter_circonstances": {
        "name": "consulter_circonstances",
        "description": (
            "Consulter les circonstances structurées et les zones de dommages annoncées "
            "pour les comparer aux éléments visibles."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
}

OUTILS_PAR_CATEGORIE = {
    "fnol": ("consulter_police", "inventorier_pieces"),
    "vision": (
        "consulter_vehicule_assure",
        "consulter_bien_assure",
        "consulter_circonstances",
        "inventorier_pieces",
    ),
}

# Défense en profondeur et documentation exécutable de la frontière de sécurité.
OUTILS_FINANCIERS_INTERDITS = frozenset({
    "calculer_indemnite",
    "evaluer_garanties",
    "modifier_montant",
    "valider_paiement",
    "changer_etat_dossier",
})


def definitions_pour(categorie: str) -> list[dict]:
    return [DEFINITIONS[nom] for nom in OUTILS_PAR_CATEGORIE.get(categorie, ())]


def noms_pour(categorie: str) -> list[str]:
    return list(OUTILS_PAR_CATEGORIE.get(categorie, ()))


def _police(dossier: Dossier, session: Session) -> Police:
    police = session.get(Police, dossier.police_id)
    if not police:
        raise ValueError(f"Police {dossier.police_id} introuvable")
    return police


def executer_outil(
    categorie: str,
    nom: str,
    entree: dict[str, Any],
    dossier: Dossier,
    session: Session,
) -> dict:
    """Exécute un outil autorisé sans mutation de la session ni du dossier."""
    autorises = OUTILS_PAR_CATEGORIE.get(categorie, ())
    if nom not in autorises or nom in OUTILS_FINANCIERS_INTERDITS:
        raise OutilInterdit(f"Outil '{nom}' non autorisé pour la catégorie '{categorie}'")
    if entree:
        raise ValueError(f"L'outil '{nom}' n'accepte aucun paramètre")

    if nom == "consulter_police":
        police = _police(dossier, session)
        return {
            "numero": police.numero,
            "formule": police.formule,
            "prime_payee": police.prime_payee,
            "vehicule": police.vehicule,
            "garanties_souscrites": sorted(police.garanties.keys()),
        }
    if nom == "consulter_vehicule_assure":
        return dict(_police(dossier, session).vehicule or {})
    if nom == "consulter_bien_assure":
        return dict(_police(dossier, session).vehicule or {})
    if nom == "inventorier_pieces":
        return {
            "nombre": len(dossier.pieces),
            "pieces": [
                {
                    "type": piece.get("type"),
                    "nom_fichier": str(piece.get("chemin", "")).replace("\\", "/").split("/")[-1],
                }
                for piece in dossier.pieces
            ],
        }
    if nom == "consulter_circonstances":
        fnol = dossier.donnees_fnol or {}
        return {
            "type_sinistre": fnol.get("type_sinistre"),
            "circonstances": fnol.get("circonstances") or dossier.declaration_texte[:500],
            "declaration_originale": dossier.declaration_texte[:500],
        }
    raise OutilInterdit(f"Outil inconnu : {nom}")
