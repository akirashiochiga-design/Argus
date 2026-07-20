"""Registre fermé des adaptateurs autorisés par Argus."""
from .base import Connecteur


_CONNECTEURS: dict[str, Connecteur] = {}


def enregistrer(connecteur: Connecteur) -> None:
    if connecteur.identifiant in _CONNECTEURS:
        raise ValueError(f"Connecteur déjà enregistré : {connecteur.identifiant}")
    _CONNECTEURS[connecteur.identifiant] = connecteur


def obtenir(identifiant: str) -> Connecteur:
    try:
        return _CONNECTEURS[identifiant]
    except KeyError as e:
        raise KeyError(f"Connecteur inconnu : {identifiant}") from e


def catalogue() -> list[dict]:
    return [
        {
            "identifiant": connecteur.identifiant,
            "nom": connecteur.nom,
            "direction": connecteur.direction,
        }
        for connecteur in _CONNECTEURS.values()
    ]
