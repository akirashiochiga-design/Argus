"""Agent 5 — Calcul d'indemnité. CODE DÉTERMINISTE, AUCUN APPEL LLM.

montant = (base facture − vétusté selon barème) − franchise, plafonné, ≥ 0.
Chaque ligne du calcul est sourcée (document, barème, clause) : c'est la
transparence qu'on montre au gestionnaire dans la file d'approbation.
"""
from datetime import date

from sqlmodel import Session

from ..models import Agent, Dossier, Police


def _taux_vetuste(bareme: list[dict], age: int) -> float:
    for tranche in sorted(bareme, key=lambda t: t["age_max"]):
        if age <= tranche["age_max"]:
            return tranche["taux"]
    return bareme[-1]["taux"] if bareme else 0.0


def executer(agent: Agent, dossier: Dossier, session: Session) -> dict:
    position = dossier.position_couverture or {}
    detail: list[dict] = []

    if not position.get("couvert"):
        detail.append({
            "etape": "position de couverture",
            "valeur": 0.0,
            "source": f"non couvert ({position.get('motif_refus', 'inconnu')}) — voir moteur de garanties",
        })
        return {
            "montant_recommande": 0.0,
            "detail_calcul": detail,
            "recommandation": "refus",
            "confiance": 1.0, "cout": 0.0, "duree_ms": 1, "mode": "deterministe",
        }

    police = session.get(Police, dossier.police_id)
    base = dossier.montant_estime
    if base is None:
        detail.append({
            "etape": "base indemnisable",
            "valeur": None,
            "source": "aucun montant extrait des documents — pièce chiffrée à demander",
        })
        return {
            "montant_recommande": None,
            "detail_calcul": detail,
            "recommandation": "demande_piece",
            "confiance": 0.3, "cout": 0.0, "duree_ms": 1, "mode": "deterministe",
        }

    detail.append({"etape": "base indemnisable", "valeur": base, "source": "total extrait de la facture/devis (agent extraction)"})

    # Vétusté — sur les garanties concernées uniquement (pas le bris de glace)
    bareme = agent.garde_fous.get("bareme_vetuste", [])
    garanties_vetuste = agent.garde_fous.get("vetuste_garanties", ["collision", "vol_incendie"])
    montant = base
    if position["garantie"] in garanties_vetuste and bareme:
        annee = (police.vehicule or {}).get("annee")
        age = max(0, date.today().year - annee) if annee else 0
        taux = _taux_vetuste(bareme, age)
        deduction = round(base * taux, 2)
        montant = round(montant - deduction, 2)
        detail.append({
            "etape": f"vétusté {int(taux * 100)} % (véhicule {annee}, {age} ans)",
            "valeur": -deduction,
            "source": "barème de vétusté (configuration de l'agent, v" + str(agent.version) + ")",
        })
    else:
        detail.append({"etape": "vétusté", "valeur": 0.0, "source": f"non applicable à la garantie '{position['garantie']}'"})

    # Franchise
    franchise = float(position.get("franchise") or 0.0)
    montant = round(montant - franchise, 2)
    detail.append({"etape": "franchise contractuelle", "valeur": -franchise, "source": "Art. 8 — grille de franchise de la police"})

    # Plafond
    plafond = position.get("plafond")
    if plafond and montant > plafond:
        detail.append({"etape": "plafonnement", "valeur": float(plafond) - montant, "source": "Art. 9 — plafond de la garantie"})
        montant = float(plafond)

    montant = max(0.0, round(montant, 2))
    detail.append({"etape": "MONTANT RECOMMANDÉ", "valeur": montant, "source": "barème et garanties contractuelles"})

    return {
        "montant_recommande": montant,
        "detail_calcul": detail,
        "recommandation": "reglement",
        "confiance": 1.0, "cout": 0.0, "duree_ms": 1, "mode": "deterministe",
    }
