"""Réinitialisation des données de référence."""
from fastapi import APIRouter

from ..seed import seed

router = APIRouter(tags=["admin"])


@router.post("/admin/reseed")
def reseed(inclure_dossiers: bool = False) -> dict:
    seed(inclure_dossiers=inclure_dossiers)
    return {"statut": "ok", "message": "Données restaurées à l'état de référence"}
