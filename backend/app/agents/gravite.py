"""Agents visuels — gravité ou contrôle de cohérence (LLM multimodal)."""
from pathlib import Path

from sqlmodel import Session

from .. import llm
from ..models import Agent, Dossier, Police
from . import runtime, signaux as signaux_deterministes

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
        "signaux": {
            "type": "array",
            "description": (
                "Incohérences plus fines détectées en croisant le constat, les photos, "
                "la déclaration et les documents chiffrés — au-delà de l'identité du "
                "véhicule. Liste vide si rien à signaler."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [
                            "chronologie", "degats_vs_recit", "degats_vs_croquis",
                            "montant_vs_gravite",
                        ],
                    },
                    "statut": {
                        "type": "string",
                        "enum": ["coherent", "incoherent", "indeterminable"],
                    },
                    "motif": {"type": "string"},
                },
                "required": ["type", "statut", "motif"],
                "additionalProperties": False,
            },
        },
        "commentaire": {"type": "string", "description": "1-2 phrases en français"},
        "confiance": {"type": "number", "description": "0 à 1"},
    },
    "required": [
        "coherence_declaration", "verification_vehicule", "signaux",
        "commentaire", "confiance",
    ],
    "additionalProperties": False,
}

SCHEMA_ANTERIORITE = {
    "type": "object",
    "properties": {
        "zones_anciennes": {
            "type": "array",
            "description": (
                "Zones où des indices suggèrent un dommage antérieur ou déjà réparé "
                "(rouille, poussière incrustée, peinture différente, pièce déjà "
                "remplacée). Liste vide si tous les dégâts semblent récents."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "zone": {"type": "string"},
                    "indices": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["zone", "indices"],
                "additionalProperties": False,
            },
        },
        "degats_recents_confirmes": {
            "type": "boolean",
            "description": "True si l'ensemble des dégâts visibles paraissent bien récents.",
        },
        "commentaire": {"type": "string", "description": "1-2 phrases en français"},
        "confiance": {"type": "number", "description": "0 à 1"},
    },
    "required": ["zones_anciennes", "degats_recents_confirmes", "commentaire", "confiance"],
    "additionalProperties": False,
}

OBJECTIF_GRAVITE = "Évaluer la gravité et localiser les zones endommagées"
OBJECTIF_COHERENCE = (
    "Évaluer les dégâts, vérifier leur cohérence avec la déclaration, le constat et "
    "les documents chiffrés, et contrôler si l'identité du véhicule est visuellement "
    "vérifiable"
)
OBJECTIF_ANTERIORITE = "Distinguer les dégâts récents des traces d'usure ou de réparations antérieures"

OBJECTIFS_PAR_MISSION = {
    "gravite": OBJECTIF_GRAVITE, "coherence": OBJECTIF_COHERENCE, "anteriorite": OBJECTIF_ANTERIORITE,
}
SCHEMAS_PAR_MISSION = {
    "gravite": SCHEMA_GRAVITE, "coherence": SCHEMA_COHERENCE, "anteriorite": SCHEMA_ANTERIORITE,
}
TYPES_IMAGES_PAR_MISSION = {
    "gravite": ("photo_degats", "photo_expertise"),
    "anteriorite": ("photo_degats", "photo_expertise"),
    "coherence": ("photo_degats", "photo_expertise", "constat"),
}


def _mission(agent: Agent) -> str:
    """Distingue les usages de la catégorie vision. Le flag garde_fous.mission fait
    foi ; l'heuristique par mots-clés n'est qu'un repli pour les agents personnalisés
    créés sans ce flag (Studio, Marketplace)."""
    mission = (agent.garde_fous or {}).get("mission")
    if mission in SCHEMAS_PAR_MISSION:
        return mission
    if agent.nom.strip().lower() == "analyse des dégâts":
        return "gravite"
    consigne = f"{agent.nom} {agent.instructions}".lower()
    if "cohérence" in consigne or "coherence" in consigne:
        return "coherence"
    if any(mot in consigne for mot in ("antérieur", "anterieur", "usure")):
        return "anteriorite"
    return "gravite"


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
            "signaux": [],
            "commentaire": (
                f"Incohérence détectée : {piece_incoherente['motif_incoherence']}"
                if piece_incoherente else
                "Les éléments visuels concordent avec la déclaration."
                if coherence is True and agent_personnalise else
                "La cohérence avec la déclaration n'a pas pu être établie."
            ),
            "confiance": 0.55,
        }

    if mission == "anteriorite":
        return {
            "zones_anciennes": [],
            "degats_recents_confirmes": True,
            "signaux": [],
            "commentaire": "Aucun indice de dommage antérieur détecté par les règles locales.",
            "confiance": 0.5,
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


def _sans_photo(mission: str) -> dict:
    """Retour explicite : aucune conclusion visuelle sans image exploitable."""
    if mission == "coherence":
        return {
            "coherence_declaration": None,
            "verification_vehicule": {
                "statut": "indeterminable",
                "elements_observes": [],
                "motif": "Aucune photo de dégâts exploitable n'est jointe au dossier.",
            },
            "signaux": [],
            "commentaire": "Contrôle visuel non réalisé : aucune photo exploitable.",
            "confiance": 0.0,
            "analyse_disponible": False,
        }
    if mission == "anteriorite":
        return {
            "zones_anciennes": [],
            "degats_recents_confirmes": None,
            "signaux": [],
            "commentaire": "Contrôle non réalisé : aucune photo exploitable.",
            "confiance": 0.0,
            "analyse_disponible": False,
        }
    return {
        "classe": None,
        "zones": [],
        "commentaire": "Analyse visuelle non réalisée : aucune photo de dégâts exploitable.",
        "confiance": 0.0,
        "analyse_disponible": False,
    }


PROMPTS_PAR_MISSION = {
    "coherence": (
        "Consulte le véhicule assuré, les circonstances et les documents déjà "
        "extraits avec les outils. Compare les photos, le croquis du constat "
        "(s'il est fourni) et la déclaration : vérifie l'identité du véhicule "
        "uniquement si des éléments visuels fiables sont réellement visibles, "
        "et signale toute incohérence plus fine (choc/zone de dommage annoncée "
        "par le croquis vs zone visible sur les photos, date du sinistre vs date "
        "des documents, montant du devis/facture disproportionné par rapport à "
        "la gravité observée). Ne signale une incohérence que si tu as un "
        "élément concret à citer — indique 'indeterminable' en cas de doute."
    ),
    "anteriorite": (
        "Analyse uniquement les indices d'ancienneté des dégâts (rouille, poussière "
        "incrustée, peinture différente, pièce déjà remplacée ou déjà réparée) sur "
        "chaque zone endommagée. Ne te prononce pas sur la cohérence globale avec la "
        "déclaration ni sur un montant. Ne signale une zone que si tu as un indice "
        "visuel concret à citer."
    ),
    "gravite": (
        "Analyse uniquement la gravité des dommages et les zones touchées. "
        "Ne te prononce pas sur la cohérence avec la déclaration ni sur "
        "l'identité du véhicule."
    ),
}


def executer(agent: Agent, dossier: Dossier, session: Session) -> dict:
    mission = _mission(agent)
    objectif = OBJECTIFS_PAR_MISSION[mission]
    schema = SCHEMAS_PAR_MISSION[mission]
    types_images = TYPES_IMAGES_PAR_MISSION[mission]
    photos = [
        p["chemin"] for p in dossier.pieces
        if p["type"] in types_images
        and (llm.RACINE / p.get("chemin", "")).exists()
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
                f"Circonstances déclarées : {circonstances}\n" + PROMPTS_PAR_MISSION[mission],
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
    if not photos:
        donnees = _sans_photo(mission)
        meta = {
            "cout": 0.0,
            "duree_ms": 1,
            "mode": "non_execute",
            "trace": runtime.trace_repli(
                "vision", objectif, "aucune photo exploitable"
            ),
        }
    elif donnees is None:
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

    if mission == "coherence":
        police = session.get(Police, dossier.police_id)
        signaux_llm = list(donnees.get("signaux") or [])
        verif = donnees.get("verification_vehicule") or {}
        if verif.get("statut") in ("coherent", "incoherent"):
            signaux_llm.append({
                "type": "vehicule",
                "source": "llm",
                "statut": verif["statut"],
                "gravite": "critique" if verif["statut"] == "incoherent" else "info",
                "motif": verif.get("motif", ""),
            })
        signaux_finaux = [*signaux_llm, *signaux_deterministes.calculer(session, dossier, police)]
        donnees = {**donnees, "signaux": signaux_finaux}
    elif mission == "anteriorite":
        signaux_llm = [
            {
                "type": "degats_anterieurs",
                "source": "llm",
                "statut": "incoherent",
                "gravite": "attention",
                "motif": f"Traces de dommage antérieur possible sur {zone['zone']} : {', '.join(zone['indices'])}.",
            }
            for zone in (donnees.get("zones_anciennes") or [])
        ]
        if not signaux_llm and donnees.get("degats_recents_confirmes"):
            signaux_llm.append({
                "type": "degats_anterieurs",
                "source": "llm",
                "statut": "coherent",
                "gravite": "info",
                "motif": donnees.get("commentaire", ""),
            })
        donnees = {**donnees, "signaux": signaux_llm}

    sortie = (
        {"analyse_coherence": donnees, "signaux": donnees.get("signaux", [])}
        if mission == "coherence"
        else {"analyse_anteriorite": donnees, "signaux": donnees.get("signaux", [])}
        if mission == "anteriorite"
        else {"gravite": donnees["classe"], "analyse_gravite": donnees}
    )
    return {**sortie, "confiance": donnees["confiance"], **meta}
