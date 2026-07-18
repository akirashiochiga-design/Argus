"""Agent 3 — Tri de gravité par vision (LLM multimodal).

Photos de dégâts + circonstances FNOL → classe léger/moyen/lourd, zones,
cohérence photo/déclaration, confiance.
Fallback simulation : estimation sur les circonstances déclarées, confiance
réduite, note explicite que les photos n'ont pas pu être analysées.
"""
from pathlib import Path

from sqlmodel import Session

from .. import llm
from ..models import Agent, Dossier

SCHEMA = {
    "type": "object",
    "properties": {
        "classe": {"type": "string", "enum": ["leger", "moyen", "lourd"]},
        "zones": {"type": "array", "items": {"type": "string"}},
        "coherence_declaration": {"type": "boolean"},
        "commentaire": {"type": "string", "description": "1-2 phrases en français"},
        "confiance": {"type": "number", "description": "0 à 1"},
    },
    "required": ["classe", "zones", "coherence_declaration", "commentaire", "confiance"],
    "additionalProperties": False,
}


def _fallback(dossier: Dossier) -> dict:
    texte = dossier.declaration_texte.lower()
    fnol = dossier.donnees_fnol or {}
    if fnol.get("type_sinistre") == "bris_glace" or "pare-brise" in texte:
        classe, zones = "leger", ["pare-brise"]
    elif "capot" in texte or ("pare-chocs" in texte and ("phare" in texte or "aile" in texte)):
        classe, zones = "moyen", [z for z in ("pare-chocs", "phare", "aile", "capot") if z in texte]
    else:
        classe, zones = "moyen", ["avant du véhicule"]
    return {
        "classe": classe,
        "zones": zones,
        "coherence_declaration": True,
        "commentaire": "Estimation sur les circonstances déclarées — photos non analysées (mode simulation).",
        "confiance": 0.55,
    }


def executer(agent: Agent, dossier: Dossier, session: Session) -> dict:
    photos = [
        p["chemin"] for p in dossier.pieces
        if p["type"] == "photo_degats" and (llm.RACINE / p.get("chemin", "")).exists()
    ]
    circonstances = (dossier.donnees_fnol or {}).get("circonstances", dossier.declaration_texte[:300])

    donnees, meta = None, None
    if photos:
        try:
            resultat = llm.generer_json(
                agent.instructions,
                f"Circonstances déclarées : {circonstances}\n"
                "Analyse les photos de dégâts jointes et classe la gravité.",
                SCHEMA,
                images=photos,
            )
            donnees = resultat["donnees"]
            meta = {"cout": resultat["cout"], "duree_ms": resultat["duree_ms"], "mode": "llm"}
        except llm.LLMIndisponible:
            pass
    if donnees is None:
        donnees = _fallback(dossier)
        meta = {"cout": 0.0, "duree_ms": 5, "mode": "simulation"}

    return {"gravite": donnees["classe"], "analyse_gravite": donnees, "confiance": donnees["confiance"], **meta}
