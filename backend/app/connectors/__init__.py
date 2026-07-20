"""Connecteurs de données externes disponibles dans Norix."""
from .documents_local import ConnecteurDocumentsLocal
from .erp_stub import ConnecteurERPDemo
from .erp_tn import construire_tous as construire_erp_tn
from .insurance_sqlite import ConnecteurAssuranceSQLite
from .registry import catalogue, enregistrer, obtenir


enregistrer(ConnecteurAssuranceSQLite())
enregistrer(ConnecteurDocumentsLocal())
enregistrer(ConnecteurERPDemo())
for _connecteur_tn in construire_erp_tn():
    enregistrer(_connecteur_tn)

__all__ = ["catalogue", "obtenir"]
