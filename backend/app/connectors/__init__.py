"""Connecteurs de données externes disponibles dans Argus."""
from .documents_local import ConnecteurDocumentsLocal
from .erp_stub import ConnecteurERPDemo
from .insurance_sqlite import ConnecteurAssuranceSQLite
from .registry import catalogue, enregistrer, obtenir


enregistrer(ConnecteurAssuranceSQLite())
enregistrer(ConnecteurDocumentsLocal())
enregistrer(ConnecteurERPDemo())

__all__ = ["catalogue", "obtenir"]
