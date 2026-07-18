"""Helper unique d'écriture de la piste d'audit.

Toute transition d'état, tout run d'agent, toute décision humaine passe par
`tracer()`. Aucun autre module n'écrit dans EvenementAudit — c'est ce qui
garantit l'exhaustivité de la piste (principe M1.6 : auditabilité par défaut).
La table est append-only : aucun endpoint UPDATE/DELETE n'existe.
"""
from typing import Optional

from sqlmodel import Session

from .models import EvenementAudit


def tracer(
    session: Session,
    acteur: str,
    acteur_type: str,  # "agent" | "humain"
    type: str,  # run_agent | decision_humaine | changement_etat | creation_agent | ...
    objet: str,  # "dossier:SIN-2026-001", "agent:7", "tache:3"
    avant: Optional[dict] = None,
    apres: Optional[dict] = None,
    motif: Optional[str] = None,
) -> EvenementAudit:
    evt = EvenementAudit(
        acteur=acteur,
        acteur_type=acteur_type,
        type=type,
        objet=objet,
        avant=avant or {},
        apres=apres or {},
        motif=motif,
    )
    session.add(evt)
    return evt
