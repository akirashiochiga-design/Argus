"""KPI du dashboard de supervision."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from .. import llm
from ..db import get_session
from ..models import Dossier, Run, Tache

# Hypothèse pitch : ~2h de traitement manuel par dossier vs ~8 min avec Norix
MINUTES_ECONOMISEES_PAR_DOSSIER = 110
# Cours USD/TND (juillet 2026) — uniquement pour l'affichage du coût IA au dashboard
USD_VERS_TND = 2.96
# Nombre de jours affichés dans la courbe des requêtes LLM du dashboard
JOURS_HISTORIQUE_REQUETES = 14

router = APIRouter(tags=["dashboard"])


def _requetes_llm(run: Run) -> int:
    """Compte les appels API réellement effectués par ce run (0 pour le code déterministe).

    'llm' = un seul appel. 'agent_outille' consulte des outils avant sa réponse finale :
    le nombre d'itérations tracées est le nombre réel d'appels (voir agents/runtime.py).
    """
    sorties = run.sorties or {}
    mode = sorties.get("mode")
    if mode == "llm":
        return 1
    if mode == "agent_outille":
        return int((sorties.get("trace") or {}).get("iterations") or 1)
    return 0


@router.get("/dashboard/kpi")
def kpi(session: Session = Depends(get_session)) -> dict:
    dossiers = session.exec(select(Dossier)).all()
    runs = session.exec(select(Run)).all()
    taches = session.exec(select(Tache).where(Tache.etat == "decidee")).all()

    par_etat: dict[str, int] = {}
    for d in dossiers:
        par_etat[d.etat] = par_etat.get(d.etat, 0) + 1

    traites = [d for d in dossiers if d.etat in ("regle", "refuse", "cloture")]
    duree_totale_ms = sum(r.duree_ms for r in runs)

    requetes_par_jour: dict[str, int] = {}
    for r in runs:
        n = _requetes_llm(r)
        if n:
            jour = r.horodatage.date().isoformat()
            requetes_par_jour[jour] = requetes_par_jour.get(jour, 0) + n
    aujourdhui = datetime.now(timezone.utc).date().isoformat()

    # Taux d'approbation et de correction (écart humain vs proposition agent)
    decisions_ok = [t for t in taches if t.decision in ("approuver", "modifier")]
    corrections = [
        abs((session.get(Dossier, t.dossier_id).montant_valide or 0) - t.montant) / t.montant
        for t in taches
        if t.decision == "modifier" and t.montant
    ]

    return {
        "dossiers_total": len(dossiers),
        "dossiers_par_etat": par_etat,
        "dossiers_traites": len(traites),
        "runs_total": len(runs),
        "cout_ia_usd": round(sum(r.cout for r in runs), 4),
        "cout_ia_dt": round(sum(r.cout for r in runs) * USD_VERS_TND, 3),
        "duree_pipeline_totale_s": round(duree_totale_ms / 1000, 1),
        "taux_approbation": round(len(decisions_ok) / len(taches), 2) if taches else None,
        "taux_correction": round(sum(corrections) / len(corrections), 3) if corrections else 0.0,
        "temps_economise_min": len(traites) * MINUTES_ECONOMISEES_PAR_DOSSIER,
        "decisions_humaines": len(taches),
        "requetes_llm_aujourdhui": requetes_par_jour.get(aujourdhui, 0),
        "requetes_llm_total": sum(requetes_par_jour.values()),
        "requetes_llm_quota_jour": llm.QUOTA_REQUETES_JOUR,
        "requetes_llm_par_jour": [
            {"date": jour, "requetes": n}
            for jour, n in sorted(requetes_par_jour.items())
        ][-JOURS_HISTORIQUE_REQUETES:],
    }
