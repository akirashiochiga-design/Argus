"""Package des serveurs MCP locaux (BDD + ERP)."""
from .bdd_sqlite import construire as construire_bdd
from .erp_finance import construire as construire_erp

__all__ = ["construire_bdd", "construire_erp"]
