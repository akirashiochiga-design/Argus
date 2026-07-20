"""Contrat minimal commun aux adaptateurs de systèmes externes."""
from typing import Protocol

from sqlmodel import Session


class Connecteur(Protocol):
    identifiant: str
    nom: str
    direction: str

    def tester(self) -> dict:
        """Valider la disponibilité et retourner des métadonnées non sensibles."""

    def synchroniser(self, session: Session) -> dict:
        """Exécuter une opération idempotente et auditée."""
