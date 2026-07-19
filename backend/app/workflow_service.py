"""Validation et sélection des traitements métier."""
from sqlmodel import Session, select

from .models import Agent, Workflow


ORDRE_CATEGORIES = {
    "fnol": 0,
    "extraction": 1,
    "vision": 2,
    "garanties": 3,
    "indemnite": 4,
    "hitl": 5,
    "courrier": 6,
}
CATEGORIES_OBLIGATOIRES = {"fnol", "garanties", "indemnite", "hitl", "courrier"}


class TraitementInvalide(ValueError):
    """Le traitement ne respecte pas les dépendances ou la gouvernance."""


def valider_etapes(session: Session, agent_ids: list[int]) -> list[dict]:
    """Valide les modules choisis et retourne des étapes normalisées."""
    if len(agent_ids) != len(set(agent_ids)):
        raise TraitementInvalide("Un même module ne peut apparaître qu'une fois")
    if not agent_ids:
        raise TraitementInvalide("Ajoutez au moins une étape au traitement")

    modules = []
    for agent_id in agent_ids:
        module = session.get(Agent, agent_id)
        if not module:
            raise TraitementInvalide(f"Module {agent_id} introuvable")
        if module.statut != "live":
            raise TraitementInvalide(f"Le module « {module.nom} » doit être publié")
        if module.categorie not in ORDRE_CATEGORIES:
            raise TraitementInvalide(f"Le module « {module.nom} » n'est pas compatible avec ce traitement")
        modules.append(module)

    categories = [module.categorie for module in modules]
    doublons = {
        categorie
        for categorie in ("garanties", "indemnite", "hitl", "courrier")
        if categories.count(categorie) > 1
    }
    if doublons:
        raise TraitementInvalide(
            "Les contrôles financiers, la validation et le courrier ne peuvent apparaître qu'une fois"
        )
    manquantes = CATEGORIES_OBLIGATOIRES - set(categories)
    if manquantes:
        libelles = {
            "fnol": "qualification initiale",
            "garanties": "contrôle des garanties",
            "indemnite": "évaluation indemnitaire",
            "hitl": "validation gestionnaire",
            "courrier": "courrier de décision",
        }
        raise TraitementInvalide(
            "Étapes obligatoires manquantes : "
            + ", ".join(libelles[categorie] for categorie in sorted(manquantes))
        )
    rangs = [ORDRE_CATEGORIES[categorie] for categorie in categories]
    if rangs != sorted(rangs):
        raise TraitementInvalide(
            "L'ordre des étapes doit suivre la qualification, les contrôles, "
            "l'évaluation, la validation gestionnaire puis le courrier"
        )

    return [
        {
            "ordre": ordre,
            "agent_id": module.id,
            "type": "porte_humaine" if module.categorie == "hitl" else "agent",
        }
        for ordre, module in enumerate(modules)
    ]


def traitement_actif(session: Session) -> Workflow | None:
    traitement = session.exec(
        select(Workflow).where(
            Workflow.statut == "live",
            Workflow.est_defaut == True,  # noqa: E712
        )
    ).first()
    if traitement:
        return traitement
    return session.exec(
        select(Workflow).where(Workflow.statut == "live").order_by(Workflow.id)
    ).first()
