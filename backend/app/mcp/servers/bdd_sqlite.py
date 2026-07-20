"""Serveur MCP local — tools lecture seule sur CoreSinistre (SQLite)."""
from __future__ import annotations

import time
from typing import Any

from ...connectors import insurance_sqlite as core
from ..protocol import McpServerLocal, McpToolDef


def _ping(_args: dict, _session: Any) -> dict:
    debut = time.monotonic()
    info = core.tester_connexion()
    return {
        "ok": True,
        "source": info["source"],
        "organisation": info.get("organisation"),
        "latence_ms": int((time.monotonic() - debut) * 1000),
    }


def _apercu_schema(_args: dict, _session: Any) -> dict:
    info = core.tester_connexion()
    return {
        "tables": info["tables"],
        "schema_version": info.get("schema_version"),
        "compteurs": info["compteurs"],
        "fichier": info["fichier"],
    }


def _lire_polices(_args: dict, _session: Any) -> dict:
    with core._connexion() as connexion:
        polices = core._polices_source(connexion)
    return {"polices": polices, "count": len(polices)}


def _lire_sinistres(_args: dict, _session: Any) -> dict:
    with core._connexion() as connexion:
        lignes = connexion.execute(
            """SELECT s.id, s.reference, s.declaration, p.numero AS police_numero
               FROM sinistres s
               JOIN polices p ON p.id = s.police_id
               ORDER BY s.reference"""
        )
        sinistres = []
        for source in lignes:
            sinistres.append(
                {
                    "id": source["id"],
                    "reference": source["reference"],
                    "declaration": source["declaration"],
                    "police_numero": source["police_numero"],
                    "pieces": core._pieces_source(connexion, source["id"]),
                }
            )
    return {"sinistres": sinistres, "count": len(sinistres)}


def construire() -> McpServerLocal:
    tools = {
        "ping": (
            McpToolDef(
                name="ping",
                description="Vérifie la disponibilité du SI assurance via MCP.",
                input_schema={"type": "object", "properties": {}},
            ),
            _ping,
        ),
        "apercu_schema": (
            McpToolDef(
                name="apercu_schema",
                description="Liste les tables et compteurs du schéma CoreSinistre.",
                input_schema={"type": "object", "properties": {}},
            ),
            _apercu_schema,
        ),
        "lire_polices": (
            McpToolDef(
                name="lire_polices",
                description="Lit les polices, véhicules et garanties (lecture seule).",
                input_schema={"type": "object", "properties": {}},
            ),
            _lire_polices,
        ),
        "lire_sinistres": (
            McpToolDef(
                name="lire_sinistres",
                description="Lit les sinistres et pièces associées (lecture seule).",
                input_schema={"type": "object", "properties": {}},
            ),
            _lire_sinistres,
        ),
    }
    return McpServerLocal("mcp-bdd-coresinistre", tools)
