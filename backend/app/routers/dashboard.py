"""KPI du dashboard de supervision."""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models import Dossier, Run, Tache

# Hypothèse pitch : ~2h de traitement manuel par dossier vs ~8 min avec Norix
MINUTES_ECONOMISEES_PAR_DOSSIER = 110
# Cours USD/TND (juillet 2026) — uniquement pour l'affichage du coût IA au dashboard
USD_VERS_TND = 2.96

router = APIRouter(tags=["dashboard"])


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
    }
