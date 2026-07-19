"""Runtime commun des agents IA outillés Argus."""
from typing import Optional

from sqlmodel import Session

from .. import llm
from ..models import Agent, Dossier
from . import tools


REGLES_SYSTEME = """

Règles d'exécution Argus :
- Utilise les outils autorisés pour consulter les faits métier avant de conclure.
- Les outils sont en lecture seule.
- Ne calcule, ne valide et ne modifie jamais un montant d'indemnisation.
- Si une information visuelle ou contractuelle n'est pas vérifiable, indique
  explicitement qu'elle est indéterminable au lieu de l'inventer.
""".strip()


def executer(
    agent: Agent,
    dossier: Dossier,
    session: Session,
    objectif: str,
    prompt: str,
    schema: dict,
    images: Optional[list[str]] = None,
) -> dict:
    """Exécute une boucle outillée dans la liste blanche de la catégorie."""
    definitions = tools.definitions_pour(agent.categorie)
    if not definitions:
        raise ValueError(f"Aucun outil déclaré pour la catégorie '{agent.categorie}'")
    max_iterations = int((agent.garde_fous or {}).get("max_iterations_agent", 4))
    max_iterations = min(6, max(2, max_iterations))

    resultat = llm.generer_json_avec_outils(
        system=f"{agent.instructions}\n\n{REGLES_SYSTEME}",
        texte_utilisateur=prompt,
        schema=schema,
        outils=definitions,
        executer_outil=lambda nom, entree: tools.executer_outil(
            agent.categorie, nom, entree, dossier, session
        ),
        images=images,
        max_iterations=max_iterations,
    )
    return {
        **resultat,
        "trace": {
            "objectif": objectif,
            "actions": resultat["actions"],
            "iterations": resultat["iterations"],
            "outils_autorises": tools.noms_pour(agent.categorie),
            "mode": "agent_outille",
        },
    }


def trace_repli(categorie: str, objectif: str, motif: str) -> dict:
    """Trace compatible UI lorsqu'un agent utilise son repli local."""
    motif_public = (
        "Aucune photo exploitable n'est disponible."
        if "aucune photo" in motif.lower()
        else "Analyse indisponible ; traitement effectué selon le barème interne."
    )
    return {
        "objectif": objectif,
        "actions": [{
            "ordre": 1,
            "type": "repli",
            "outil": "regles_locales",
            "entree": {},
            "resultat": {"motif": motif_public},
            "statut": "succes",
            "duree_ms": 5,
        }],
        "iterations": 0,
        "outils_autorises": tools.noms_pour(categorie),
        "mode": "regles_locales",
    }
