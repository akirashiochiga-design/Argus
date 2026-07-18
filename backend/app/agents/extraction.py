"""Agent 2 — Extraction documentaire (LLM vision, 1 appel par pièce).

Lit facture / devis / constat (image) → champs typés + confiance par champ.
Le montant EXTRAIT ici est une lecture de document, pas une décision :
le calcul d'indemnité reste 100 % déterministe (agent 5).
Fallback : reprend le montant déclaré dans le seed.
"""
from sqlmodel import Session

from .. import llm
from ..models import Agent, Dossier

SCHEMA = {
    "type": "object",
    "properties": {
        "type_document": {"type": "string", "enum": ["facture", "devis", "constat", "autre"]},
        "emetteur": {"type": "string"},
        "date": {"type": "string"},
        "immatriculations": {"type": "array", "items": {"type": "string"}},
        "postes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"libelle": {"type": "string"}, "montant": {"type": "number"}},
                "required": ["libelle", "montant"],
                "additionalProperties": False,
            },
        },
        "total": {"type": ["number", "null"], "description": "Montant total en DT, null si absent"},
        "confiance": {"type": "number", "description": "0 à 1"},
        "qualite_image": {"type": "string", "enum": ["bonne", "moyenne", "mauvaise"]},
    },
    "required": ["type_document", "emetteur", "date", "immatriculations", "postes", "total", "confiance", "qualite_image"],
    "additionalProperties": False,
}

TYPES_CHIFFRES = ("facture", "devis")


def _fallback_piece(piece: dict) -> dict:
    montant = piece.get("montant")
    return {
        "type_document": piece["type"] if piece["type"] in ("facture", "devis", "constat") else "autre",
        "emetteur": "document du dossier",
        "date": "voir document",
        "immatriculations": [],
        "postes": [{"libelle": "total document", "montant": montant}] if montant else [],
        "total": montant,
        "confiance": 0.9 if montant else 0.5,
        "qualite_image": "moyenne",
    }


def executer(agent: Agent, dossier: Dossier, session: Session) -> dict:
    pieces = list(dossier.pieces)
    cout_total, duree_totale = 0.0, 0
    modes = set()

    for piece in pieces:
        if piece["type"] == "photo_degats":
            continue  # les photos de dégâts sont pour l'agent gravité
        chemin = piece.get("chemin", "")
        try:
            resultat = llm.generer_json(
                agent.instructions,
                f"Document joint au sinistre {dossier.ref} (type annoncé : {piece['type']}). "
                "Extrais les champs. Les montants sont en dinars tunisiens (DT).",
                SCHEMA,
                images=[chemin],
            )
            extraction = resultat["donnees"]
            cout_total += resultat["cout"]
            duree_totale += resultat["duree_ms"]
            modes.add("llm")
        except llm.LLMIndisponible:
            extraction = _fallback_piece(piece)
            duree_totale += 5
            modes.add("llm")
        piece["extraction"] = extraction

    # Montant de référence pour le calcul : le total du document chiffré le plus fiable
    chiffres = [
        p["extraction"] for p in pieces
        if p.get("extraction") and p["extraction"]["type_document"] in TYPES_CHIFFRES
        and p["extraction"]["total"]
    ]
    montant_estime = None
    if chiffres:
        meilleur = max(chiffres, key=lambda e: e["confiance"])
        montant_estime = float(meilleur["total"])

    confiances = [p["extraction"]["confiance"] for p in pieces if p.get("extraction")]
    return {
        "pieces": pieces,
        "montant_estime": montant_estime,
        "confiance": round(sum(confiances) / len(confiances), 2) if confiances else None,
        "cout": round(cout_total, 6),
        "duree_ms": duree_totale,
        "mode": "llm" if modes == {"llm"} else "mixte",
    }
