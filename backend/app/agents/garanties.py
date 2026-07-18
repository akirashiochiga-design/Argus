"""Agent 4 — Moteur de garanties. CODE DÉTERMINISTE, AUCUN APPEL LLM.

Applique le contrat au sinistre : garantie couverte ? franchise ? plafond ?
Chaque conclusion est motivée ligne à ligne avec la clause citée.
"""
from sqlmodel import Session

from ..models import Agent, Dossier, Police

# type de sinistre (FNOL) -> garantie du contrat requise
GARANTIE_REQUISE = {
    "collision": "collision",
    "bris_glace": "bris_glace",
    "vol": "vol_incendie",
    "incendie": "vol_incendie",
    "vandalisme": "collision",
    "autre": "collision",
}

CLAUSES = {
    "prime_impayee": "Art. 12 — Suspension de garantie en cas de prime impayée",
    "garantie_absente": "Art. 4 — Étendue des garanties souscrites (tableau des garanties)",
    "garantie_couverte": "Art. 5 — Dommages au véhicule assuré",
    "franchise": "Art. 8 — Franchises contractuelles",
    "plafond": "Art. 9 — Plafonds d'indemnisation",
}


def executer(agent: Agent, dossier: Dossier, session: Session) -> dict:
    police = session.get(Police, dossier.police_id)
    fnol = dossier.donnees_fnol or {}
    type_sinistre = fnol.get("type_sinistre", "collision")
    garantie = GARANTIE_REQUISE.get(type_sinistre, "collision")

    motivation: list[dict] = []

    # 1. La prime est-elle à jour ?
    if not police.prime_payee:
        motivation.append({
            "regle": "prime impayée",
            "conclusion": "garantie suspendue — sinistre non couvert",
            "clause": CLAUSES["prime_impayee"],
        })
        position = {
            "couvert": False,
            "garantie": garantie,
            "motif_refus": "prime_impayee",
            "franchise": None,
            "plafond": None,
            "motivation": motivation,
        }
        return {"position_couverture": position, "confiance": 1.0, "cout": 0.0, "duree_ms": 1, "mode": "deterministe"}

    # 2. La garantie requise figure-t-elle au contrat ?
    if garantie not in police.garanties:
        motivation.append({
            "regle": f"sinistre '{type_sinistre}' → garantie requise '{garantie}'",
            "conclusion": f"garantie '{garantie}' absente de la formule '{police.formule}' — non couvert",
            "clause": CLAUSES["garantie_absente"],
        })
        if type_sinistre == "collision" and not fnol.get("tiers_identifie", False):
            motivation.append({
                "regle": "recours contre le tiers responsable",
                "conclusion": "impossible : tiers non identifié, pas de constat",
                "clause": "Art. 15 — Recours et subrogation",
            })
        position = {
            "couvert": False,
            "garantie": garantie,
            "motif_refus": "garantie_absente",
            "franchise": None,
            "plafond": None,
            "motivation": motivation,
        }
        return {"position_couverture": position, "confiance": 1.0, "cout": 0.0, "duree_ms": 1, "mode": "deterministe"}

    # 3. Couvert : franchise et plafond applicables
    conditions = police.garanties[garantie]
    motivation.append({
        "regle": f"sinistre '{type_sinistre}' → garantie '{garantie}' souscrite ({police.formule})",
        "conclusion": "sinistre couvert",
        "clause": CLAUSES["garantie_couverte"],
    })
    motivation.append({
        "regle": "franchise contractuelle",
        "conclusion": f"franchise applicable : {conditions['franchise']} DT",
        "clause": CLAUSES["franchise"],
    })
    if conditions.get("plafond"):
        motivation.append({
            "regle": "plafond d'indemnisation",
            "conclusion": f"plafond : {conditions['plafond']} DT",
            "clause": CLAUSES["plafond"],
        })

    position = {
        "couvert": True,
        "garantie": garantie,
        "motif_refus": None,
        "franchise": conditions["franchise"],
        "plafond": conditions.get("plafond"),
        "motivation": motivation,
    }
    return {"position_couverture": position, "confiance": 1.0, "cout": 0.0, "duree_ms": 1, "mode": "deterministe"}
