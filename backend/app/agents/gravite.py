"""Agent 3 — Tri de gravité par vision (LLM multimodal).

Photos de dégâts + circonstances FNOL → classe léger/moyen/lourd, zones,
cohérence photo/déclaration, confiance.
Fallback : estimation sur les circonstances déclarées, confiance
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


def _fallback(agent: Agent, dossier: Dossier) -> dict:
    texte = dossier.declaration_texte.lower()
    fnol = dossier.donnees_fnol or {}
    agent_personnalise = agent.garde_fous.get("origine") == "prompt_studio"
    photos_annotees = [
        p for p in dossier.pieces
        if p.get("type") == "photo_degats" and "coherence_attendue" in p
    ]
    piece_incoherente = next(
        (
            p for p in dossier.pieces
            if p.get("coherence_attendue") is False or p.get("incoherente_declaration")
        ),
        None,
    ) if agent_personnalise else None
    coherence = (
        False if piece_incoherente
        else True if agent_personnalise and photos_annotees
        else True if not agent_personnalise
        else None
    )
    if fnol.get("type_sinistre") == "bris_glace" or "pare-brise" in texte:
        classe, zones = "leger", ["pare-brise"]
    elif "capot" in texte or ("pare-chocs" in texte and ("phare" in texte or "aile" in texte)):
        classe, zones = "moyen", [z for z in ("pare-chocs", "phare", "aile", "capot") if z in texte]
    else:
        classe, zones = "moyen", ["avant du véhicule"]
    return {
        "classe": classe,
        "zones": zones,
        "coherence_declaration": coherence,
        "commentaire": (
            f"Incohérence détectée : {piece_incoherente['motif_incoherence']}"
            if piece_incoherente else
            "Les éléments visuels concordent avec la déclaration."
            if coherence is True and agent_personnalise else
            "La cohérence avec la déclaration n'a pas pu être établie."
            if agent_personnalise else
            "Évaluation établie à partir des circonstances déclarées."
        ),
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
        donnees = _fallback(agent, dossier)
        meta = {"cout": 0.0, "duree_ms": 5}

    return {"gravite": donnees["classe"], "analyse_gravite": donnees, "confiance": donnees["confiance"], **meta}
