"""Agent 6 — Porte de validation humaine. CODE DÉTERMINISTE, NON DÉSACTIVABLE.

Routage par seuil : sous le seuil, le règlement est "proposé" ; au-dessus,
validation obligatoire. Dans TOUS les cas une tâche humaine est créée :
aucun paiement ne part sans action humaine explicite (principe M1.6).
"""
from sqlmodel import Session, select

from ..models import Agent, Dossier, Run, Tache


def _dernier_detail_calcul(session: Session, dossier_id: int) -> list:
    runs = session.exec(
        select(Run).where(Run.dossier_id == dossier_id).order_by(Run.id.desc())
    ).all()
    for run in runs:
        if run.sorties and "detail_calcul" in run.sorties:
            return run.sorties["detail_calcul"]
    return []


def executer(agent: Agent, dossier: Dossier, session: Session) -> dict:
    seuil = float(agent.seuils.get("seuil_validation", 1000))
    montant = dossier.montant_recommande
    couvert = bool((dossier.position_couverture or {}).get("couvert"))

    if not couvert:
        type_tache, routage = "validation_refus", "refus à confirmer par un humain"
    elif montant is not None and montant >= seuil:
        type_tache, routage = "validation_reglement", f"montant {montant} DT ≥ seuil {seuil} DT — validation obligatoire"
    else:
        type_tache, routage = "validation_reglement", f"montant {montant} DT < seuil {seuil} DT — règlement proposé"

    tache = Tache(
        dossier_id=dossier.id,
        type=type_tache,
        montant=float(montant or 0.0),
        proposition={
            "routage": routage,
            "sous_seuil": bool(couvert and montant is not None and montant < seuil),
            "gravite": dossier.gravite,
            "position_couverture": dossier.position_couverture,
            "detail_calcul": _dernier_detail_calcul(session, dossier.id),
            "fnol": dossier.donnees_fnol,
        },
    )
    session.add(tache)
    session.flush()  # pour obtenir tache.id

    return {
        "tache_id": tache.id,
        "type_tache": type_tache,
        "routage": routage,
        "confiance": 1.0, "cout": 0.0, "duree_ms": 1, "mode": "deterministe",
    }
