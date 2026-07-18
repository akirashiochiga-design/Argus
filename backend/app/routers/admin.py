"""Outillage démo : réinitialiser la base au dataset calibré."""
from fastapi import APIRouter

from ..seed import seed

router = APIRouter(tags=["admin"])


@router.post("/admin/reseed")
def reseed() -> dict:
    """Bouton 'reset démo' — supprime et recrée argus.db. À utiliser entre deux répétitions."""
    seed()
    return {"statut": "ok", "message": "Base réinitialisée au dataset de démo"}
