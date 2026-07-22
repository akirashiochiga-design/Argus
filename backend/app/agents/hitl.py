"""Agent 6 — Porte de validation humaine. CODE DÉTERMINISTE, NON DÉSACTIVABLE.

Routage par seuil : sous le seuil, le règlement est "proposé" ; au-dessus,
validation obligatoire. Dans TOUS les cas une tâche humaine est créée :
aucun paiement ne part sans action humaine explicite (principe M1.6).

Capacité d'adaptation : quand l'agent 5 (indemnité) n'a pas pu chiffrer le
dossier — pièce manquante, ou tout autre cas où `base` est indisponible —
la porte route vers une tâche "demande_piece" au lieu de proposer un
règlement à 0 DT. Le gestionnaire choisit alors : la pièce arrive (il saisit
le montant via "modifier", le pipeline se termine normalement) ou l'assuré
ne répond pas (il clôture "sans_suite" — voir orchestrator.decider).
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


def _derniere_recommandation(session: Session, dossier_id: int) -> str | None:
    runs = session.exec(
        select(Run).where(Run.dossier_id == dossier_id).order_by(Run.id.desc())
    ).all()
    for run in runs:
        if run.sorties and "recommandation" in run.sorties:
            return run.sorties["recommandation"]
    return None


def executer(agent: Agent, dossier: Dossier, session: Session) -> dict:
    seuil = float(agent.seuils.get("seuil_validation", 1000))
    montant = dossier.montant_recommande
    couvert = bool((dossier.position_couverture or {}).get("couvert"))
    recommandation = _derniere_recommandation(session, dossier.id)
    signaux_alerte = [s for s in (dossier.signaux or []) if s.get("statut") == "incoherent"]

    if recommandation == "demande_piece":
        type_tache = "demande_piece"
        routage = "aucune pièce chiffrée exploitable — relancer l'assuré ou clôturer sans suite"
    elif not couvert:
        type_tache, routage = "validation_refus", "refus à confirmer par un humain"
    elif montant is not None and montant >= seuil:
        type_tache, routage = "validation_reglement", f"montant {montant} DT ≥ seuil {seuil} DT — validation obligatoire"
    else:
        type_tache, routage = "validation_reglement", f"montant {montant} DT < seuil {seuil} DT — règlement proposé"

    if signaux_alerte:
        # Un signal d'incohérence retire toujours la dossier de la file "sous seuil" :
        # même un petit montant mérite un examen humain réel, jamais un rubber-stamp.
        routage = f"⚠ {len(signaux_alerte)} signal(aux) d'incohérence à vérifier — {routage}"

    tache = Tache(
        dossier_id=dossier.id,
        type=type_tache,
        montant=float(montant or 0.0),
        proposition={
            "routage": routage,
            "sous_seuil": bool(
                couvert and montant is not None and montant < seuil and not signaux_alerte
            ),
            "gravite": dossier.gravite,
            "position_couverture": dossier.position_couverture,
            "detail_calcul": _dernier_detail_calcul(session, dossier.id),
            "fnol": dossier.donnees_fnol,
            "signaux": dossier.signaux or [],
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
