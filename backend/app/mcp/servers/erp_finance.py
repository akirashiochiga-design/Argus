"""Serveur MCP local — tools d'écriture ERP finance (après HITL)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlmodel import select

from ...audit import tracer
from ...models import Dossier, EcritureERP
from ..protocol import McpError, McpServerLocal, McpToolDef

CONNECTEUR_ID = "erp_interne_demo"


def _ping(_args: dict, _session: Any) -> dict:
    return {
        "ok": True,
        "systeme": "ERP Finance interne",
        "protocole": "MCP",
        "mode": "écriture après validation humaine",
        "latence_ms": 12,
    }


def _envoyer_ecritures_planifiees(_args: dict, session: Any) -> dict:
    if session is None:
        raise McpError("Session Norix requise pour envoyer_ecritures_planifiees")
    ecritures = session.exec(
        select(EcritureERP).where(
            EcritureERP.connecteur == CONNECTEUR_ID,
            EcritureERP.statut == "planifiee",
        )
    ).all()
    for ecriture in ecritures:
        ecriture.statut = "envoyee"
        ecriture.envoyee_le = datetime.now(timezone.utc)
        session.add(ecriture)
        dossier = session.get(Dossier, ecriture.dossier_id)
        tracer(
            session,
            acteur="systeme:mcp_erp_finance",
            acteur_type="agent",
            type="ecriture_erp_envoyee",
            objet=f"dossier:{dossier.ref if dossier else ecriture.dossier_id}",
            avant={"statut": "planifiee"},
            apres={
                "statut": "envoyee",
                "montant": ecriture.montant,
                "connecteur": CONNECTEUR_ID,
                "protocole": "MCP",
                "tool": "envoyer_ecritures_planifiees",
            },
            motif="Accusé de réception ERP via MCP après validation humaine",
        )
    session.commit()
    return {
        "statut": "succes",
        "ecritures_envoyees": len(ecritures),
        "protocole": "MCP",
        "tool": "envoyer_ecritures_planifiees",
    }


def construire() -> McpServerLocal:
    tools = {
        "ping": (
            McpToolDef(
                name="ping",
                description="Vérifie la disponibilité de l'ERP finance via MCP.",
                input_schema={"type": "object", "properties": {}},
            ),
            _ping,
        ),
        "envoyer_ecritures_planifiees": (
            McpToolDef(
                name="envoyer_ecritures_planifiees",
                description=(
                    "Envoie les écritures planifiées après validation humaine. "
                    "Ne crée jamais d'écriture sans HITL préalable."
                ),
                input_schema={"type": "object", "properties": {}},
            ),
            _envoyer_ecritures_planifiees,
        ),
    }
    return McpServerLocal("mcp-erp-finance", tools)
