"""Contrôles automatiques Marketplace — décide seule de la publication ou du refus.

La curation d'un agent soumis par un éditeur est la responsabilité de Norix, pas
de la compagnie d'assurance : cette décision est donc entièrement automatisée et
déterministe (tests programmatiques + une exécution réelle sur un dossier de
test), jamais laissée à l'appréciation d'un gestionnaire compagnie ni à un LLM
qui « trouverait ça bien ».
"""
import re

from sqlmodel import Session, select

from .agents import DISPATCH
from .agents.tools import OUTILS_FINANCIERS_INTERDITS, noms_pour
from .models import Agent, Dossier, Police

MOTIFS_SECRET = re.compile(
    r"(api[_ -]?key|mot[_ -]?de[_ -]?passe|password|secret|sk-[a-z0-9_-]{8,})",
    re.IGNORECASE,
)
MOTIFS_DECISION_ARGENT = re.compile(
    r"(valide(r|z)?\s+le\s+paiement|d[ée]cide(r|z)?\s+du\s+montant|verse(r|z)?\s+automatiquement|"
    r"rembourse(r|z)?\s+automatiquement|autorise(r|z)?\s+le\s+r[èe]glement)",
    re.IGNORECASE,
)
COUT_MAX_TEST_USD = 0.05
CATEGORIES_AVEC_DISPATCH = {"fnol", "extraction", "vision", "courrier"}


def _resultat(nom: str, statut: str, detail: str) -> dict:
    return {"nom": nom, "statut": statut, "detail": detail}


def _test_secrets(nom: str, description: str, instructions: str) -> dict:
    texte = f"{nom} {description} {instructions}"
    if MOTIFS_SECRET.search(texte):
        return _resultat(
            "absence_de_secrets", "echec",
            "Une clé, un mot de passe ou un secret a été détecté dans le texte soumis.",
        )
    return _resultat("absence_de_secrets", "reussi", "Aucun secret détecté.")


def _test_vocabulaire_financier(instructions: str) -> dict:
    if MOTIFS_DECISION_ARGENT.search(instructions):
        return _resultat(
            "pas_de_decision_financiere_induite", "echec",
            "Les instructions suggèrent que l'agent validerait ou déciderait seul d'un "
            "paiement — interdit (CLAUDE.md §5, non négociable).",
        )
    return _resultat("pas_de_decision_financiere_induite", "reussi", "Aucune formulation de décision financière détectée.")


def _test_garde_fous(garde_fous: dict, categorie: str) -> dict:
    if not garde_fous.get("pas_de_decision_argent"):
        return _resultat("garde_fous_non_contournables", "echec", "Le garde-fou 'pas_de_decision_argent' n'est pas actif.")
    autorises = set(garde_fous.get("outils_autorises") or [])
    if autorises & OUTILS_FINANCIERS_INTERDITS:
        return _resultat("garde_fous_non_contournables", "echec", "Un outil financier interdit figure dans les outils autorisés.")
    if not autorises <= set(noms_pour(categorie)):
        return _resultat("garde_fous_non_contournables", "echec", "Un outil hors du registre autorisé pour cette catégorie est présent.")
    return _resultat("garde_fous_non_contournables", "reussi", "Garde-fous conformes au registre Norix.")


def _dossier_synthetique(session: Session) -> Dossier | None:
    """Dossier transitoire (jamais persisté, id=-1) construit à partir d'assets toujours
    présents (une police du seed, des images de docs/samples/). Le test ne dépend donc
    jamais de l'état de démo (dossiers synchronisés ou non)."""
    police = session.exec(select(Police)).first()
    if not police:
        return None
    return Dossier(
        id=-1,
        ref="QA-SYNTHETIQUE",
        police_id=police.id,
        declaration_texte=(
            "Collision en stationnement. Le pare-chocs avant et le phare gauche sont "
            "endommagés. Un devis et une photo des dégâts sont joints."
        ),
        donnees_fnol={"circonstances": "Choc à l'avant, pare-chocs et phare gauche endommagés."},
        gravite="moyen",
        montant_estime=1200.0,
        position_couverture={"couvert": True, "garantie": "collision", "motivation": []},
        pieces=[
            {"type": "constat", "chemin": "docs/samples/constat.jpg"},
            {"type": "photo_degats", "chemin": "docs/samples/degats-1.jpg"},
            {"type": "devis", "chemin": "docs/samples/devis.jpg", "montant": 1200.0},
        ],
    )


def _test_execution_reelle(session: Session, nom: str, instructions: str, categorie: str, garde_fous: dict) -> dict:
    if categorie not in CATEGORIES_AVEC_DISPATCH:
        return _resultat("execution_sur_dossier_test", "non_applicable", "Catégorie hors du pipeline d'exécution automatisé.")
    dossier = _dossier_synthetique(session)
    if not dossier:
        return _resultat("execution_sur_dossier_test", "non_applicable", "Aucune police de référence disponible pour ce test.")
    agent_test = Agent(nom=nom, categorie=categorie, instructions=instructions, garde_fous=garde_fous, statut="draft")
    try:
        resultat = DISPATCH[categorie](agent_test, dossier, session)
    except Exception as e:
        return _resultat("execution_sur_dossier_test", "echec", f"L'agent a levé une erreur sur un dossier de test : {e}")
    cout = resultat.get("cout") or 0.0
    if cout > COUT_MAX_TEST_USD:
        return _resultat("execution_sur_dossier_test", "echec", f"Coût anormalement élevé pour un seul appel ({cout:.4f} $).")
    return _resultat(
        "execution_sur_dossier_test", "reussi",
        f"Exécution réussie sur un dossier de test (mode {resultat.get('mode')}, coût {cout:.4f} $).",
    )


def executer(session: Session, *, nom: str, description: str, instructions: str, categorie: str, garde_fous: dict) -> dict:
    """Fait passer la suite complète et retourne le rapport ({résultat, tests})."""
    tests = [
        _test_secrets(nom, description, instructions),
        _test_vocabulaire_financier(instructions),
        _test_garde_fous(garde_fous, categorie),
        _test_execution_reelle(session, nom, instructions, categorie, garde_fous),
    ]
    echecs = [t for t in tests if t["statut"] == "echec"]
    return {
        "resultat": "refuse" if echecs else "valide",
        "tests": tests,
    }
