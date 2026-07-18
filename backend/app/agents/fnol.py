"""Agent 1 — FNOL bilingue (LLM texte).

Entrée : declaration_texte (français ou darija tunisienne).
Sortie : dossier FNOL structuré + champs manquants + complétude + langue.
Fallback : heuristiques par mots-clés si l'API est indisponible.
"""
from sqlmodel import Session

from .. import llm
from ..models import Agent, Dossier

SCHEMA = {
    "type": "object",
    "properties": {
        "type_sinistre": {
            "type": "string",
            "enum": ["collision", "bris_glace", "vol", "incendie", "vandalisme", "autre"],
        },
        "date_sinistre": {"type": "string", "description": "Date ou moment déclaré, tel quel"},
        "lieu": {"type": "string"},
        "circonstances": {"type": "string", "description": "Résumé factuel en français, 2 phrases max"},
        "tiers_identifie": {"type": "boolean"},
        "constat_present": {"type": "boolean"},
        "pieces_annoncees": {"type": "array", "items": {"type": "string"}},
        "champs_manquants": {"type": "array", "items": {"type": "string"}},
        "completude": {"type": "number", "description": "0 à 1"},
        "langue": {"type": "string", "enum": ["fr", "darija", "mixte"]},
    },
    "required": [
        "type_sinistre", "date_sinistre", "lieu", "circonstances", "tiers_identifie",
        "constat_present", "pieces_annoncees", "champs_manquants", "completude", "langue",
    ],
    "additionalProperties": False,
}

MOTS_DARIJA = ("aslema", "salem", "ena", "el ", "3and", "mkass", "karhba", "chnoua", "bare7", "l9it")


def _fallback(dossier: Dossier) -> dict:
    """Structuration par mots-clés — fallback si API indisponible."""
    texte = dossier.declaration_texte.lower()
    if "pare-brise" in texte or "fissur" in texte or "gravier" in texte:
        type_sinistre = "bris_glace"
    elif "vol" in texte and "volant" not in texte:
        type_sinistre = "vol"
    else:
        type_sinistre = "collision"
    darija = sum(1 for m in MOTS_DARIJA if m in texte)
    constat = "constat" in texte and "ma famech" not in texte
    tiers = ("reconnu" in texte or "constat amiable" in texte) and constat
    return {
        "type_sinistre": type_sinistre,
        "date_sinistre": "déclarée dans le texte (à confirmer)",
        "lieu": "déclaré dans le texte (à confirmer)",
        "circonstances": dossier.declaration_texte[:180] + "…",
        "tiers_identifie": tiers,
        "constat_present": constat,
        "pieces_annoncees": [p["type"] for p in dossier.pieces],
        "champs_manquants": ["numéro de permis"] if constat else ["constat amiable", "numéro de permis"],
        "completude": 0.8 if constat else 0.6,
        "langue": "darija" if darija >= 2 else "fr",
    }


def executer(agent: Agent, dossier: Dossier, session: Session) -> dict:
    prompt = (
        f"Déclaration de sinistre (police {dossier.police_id}) :\n\n{dossier.declaration_texte}\n\n"
        f"Pièces jointes annoncées : {[p['type'] for p in dossier.pieces]}"
    )
    try:
        resultat = llm.generer_json(agent.instructions, prompt, SCHEMA)
        donnees = resultat["donnees"]
        meta = {"cout": resultat["cout"], "duree_ms": resultat["duree_ms"], "mode": "llm"}
    except llm.LLMIndisponible:
        donnees = _fallback(dossier)
        meta = {"cout": 0.0, "duree_ms": 5}

    return {
        "donnees_fnol": donnees,
        "confiance": donnees["completude"],
        **meta,
    }
