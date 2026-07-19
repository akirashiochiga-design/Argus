"""Agents visuels — gravité ou contrôle de cohérence (LLM multimodal)."""
from pathlib import Path

from sqlmodel import Session

from .. import llm
from ..models import Agent, Dossier
from . import runtime

SCHEMA_GRAVITE = {
    "type": "object",
    "properties": {
        "classe": {"type": "string", "enum": ["leger", "moyen", "lourd"]},
        "zones": {"type": "array", "items": {"type": "string"}},
        "commentaire": {"type": "string", "description": "1-2 phrases en français"},
        "confiance": {"type": "number", "description": "0 à 1"},
    },
    "required": ["classe", "zones", "commentaire", "confiance"],
    "additionalProperties": False,
}

SCHEMA_COHERENCE = {
    "type": "object",
    "properties": {
        "coherence_declaration": {"type": "boolean"},
        "verification_vehicule": {
            "type": "object",
            "properties": {
                "statut": {
                    "type": "string",
                    "enum": ["coherent", "incoherent", "indeterminable"],
                },
                "elements_observes": {"type": "array", "items": {"type": "string"}},
                "motif": {"type": "string"},
            },
            "required": ["statut", "elements_observes", "motif"],
            "additionalProperties": False,
        },
        "commentaire": {"type": "string", "description": "1-2 phrases en français"},
        "confiance": {"type": "number", "description": "0 à 1"},
    },
    "required": ["coherence_declaration", "verification_vehicule", "commentaire", "confiance"],
    "additionalProperties": False,
}

OBJECTIF_GRAVITE = "Évaluer la gravité et localiser les zones endommagées"
OBJECTIF_COHERENCE = (
    "Évaluer les dégâts, vérifier leur cohérence avec la déclaration et contrôler "
    "si l'identité du véhicule est visuellement vérifiable"
)


def _mission(agent: Agent) -> str:
    """Distingue les deux usages de la catégorie vision, anciens agents inclus."""
    mission = (agent.garde_fous or {}).get("mission")
    if mission in {"gravite", "coherence"}:
        return mission
    if agent.nom.strip().lower() == "analyse des dégâts":
        return "gravite"
    consigne = f"{agent.nom} {agent.instructions}".lower()
    return "coherence" if "cohérence" in consigne or "coherence" in consigne else "gravite"


def _fallback(agent: Agent, dossier: Dossier, mission: str | None = None) -> dict:
    mission = mission or _mission(agent)
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
    )
    coherence = (
        False if piece_incoherente
        else True if agent_personnalise and photos_annotees
        else True if not agent_personnalise
        else None
    )
    if mission == "coherence":
        return {
            "coherence_declaration": coherence,
            "verification_vehicule": {
                "statut": "incoherent" if piece_incoherente else "indeterminable",
                "elements_observes": (
                    ["Toyota rouge", "dommages à l'avant"]
                    if piece_incoherente else []
                ),
                "motif": (
                    piece_incoherente["motif_incoherence"]
                    if piece_incoherente else
                    "Les éléments visuels ne permettent pas d'identifier de façon fiable "
                    "la marque ou le modèle du véhicule."
                ),
            },
            "commentaire": (
                f"Incohérence détectée : {piece_incoherente['motif_incoherence']}"
                if piece_incoherente else
                "Les éléments visuels concordent avec la déclaration."
                if coherence is True and agent_personnalise else
                "La cohérence avec la déclaration n'a pas pu être établie."
            ),
            "confiance": 0.55,
        }

    if fnol.get("type_sinistre") == "bris_glace" or "pare-brise" in texte:
        classe, zones = "leger", ["pare-brise"]
    elif "capot" in texte or ("pare-chocs" in texte and ("phare" in texte or "aile" in texte)):
        classe, zones = "moyen", [z for z in ("pare-chocs", "phare", "aile", "capot") if z in texte]
    else:
        classe, zones = "moyen", ["avant du véhicule"]
    return {
        "classe": classe,
        "zones": zones,
        "commentaire": "Évaluation de la gravité établie à partir des dommages visibles.",
        "confiance": 0.55,
    }


def executer(agent: Agent, dossier: Dossier, session: Session) -> dict:
    mission = _mission(agent)
    objectif = OBJECTIF_COHERENCE if mission == "coherence" else OBJECTIF_GRAVITE
    schema = SCHEMA_COHERENCE if mission == "coherence" else SCHEMA_GRAVITE
    photos = [
        p["chemin"] for p in dossier.pieces
        if p["type"] == "photo_degats" and (llm.RACINE / p.get("chemin", "")).exists()
    ]
    circonstances = (dossier.donnees_fnol or {}).get("circonstances", dossier.declaration_texte[:300])

    donnees, meta = None, None
    if photos:
        try:
            resultat = runtime.executer(
                agent,
                dossier,
                session,
                objectif,
                (
                    f"Circonstances déclarées : {circonstances}\n"
                    + (
                        "Consulte le véhicule assuré et les circonstances avec les outils. "
                        "Compare les photos à la déclaration et vérifie l'identité du véhicule "
                        "uniquement si des éléments visuels fiables sont réellement visibles."
                        if mission == "coherence" else
                        "Analyse uniquement la gravité des dommages et les zones touchées. "
                        "Ne te prononce pas sur la cohérence avec la déclaration ni sur "
                        "l'identité du véhicule."
                    )
                ),
                schema,
                images=photos,
            )
            donnees = resultat["donnees"]
            meta = {
                "cout": resultat["cout"],
                "duree_ms": resultat["duree_ms"],
                "mode": resultat["mode"],
                "trace": resultat["trace"],
            }
        except llm.LLMIndisponible as e:
            meta = {
                "cout": 0.0,
                "duree_ms": 5,
                "mode": "regles_locales",
                "trace": runtime.trace_repli("vision", objectif, str(e)),
            }
    if donnees is None:
        donnees = _fallback(agent, dossier, mission)
        if meta is None:
            meta = {
                "cout": 0.0,
                "duree_ms": 5,
                "mode": "regles_locales",
                "trace": runtime.trace_repli(
                    "vision", objectif, "aucune photo exploitable"
                ),
            }

    sortie = (
        {"analyse_coherence": donnees}
        if mission == "coherence"
        else {"gravite": donnees["classe"], "analyse_gravite": donnees}
    )
    return {**sortie, "confiance": donnees["confiance"], **meta}
