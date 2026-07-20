"""Client MCP Norix : découvre et appelle des tools sur des serveurs locaux."""
from __future__ import annotations

from typing import Any, Optional

from sqlmodel import Session

from ..audit import tracer
from .protocol import McpError, McpServerLocal
from .servers import construire_bdd, construire_erp

_SERVEURS: dict[str, McpServerLocal] | None = None


def _registre() -> dict[str, McpServerLocal]:
    global _SERVEURS
    if _SERVEURS is None:
        _SERVEURS = {
            "bdd": construire_bdd(),
            "erp": construire_erp(),
        }
    return _SERVEURS


def serveur_bdd() -> McpServerLocal:
    return _registre()["bdd"]


def serveur_erp() -> McpServerLocal:
    return _registre()["erp"]


class McpClient:
    """Client MCP in-process (tools/list · tools/call) avec audit optionnel."""

    def __init__(self, serveur: McpServerLocal):
        self.serveur = serveur

    def list_tools(self) -> list[dict]:
        return self.serveur.list_tools()

    def call_tool(
        self,
        name: str,
        arguments: dict | None = None,
        *,
        session: Optional[Session] = None,
        auditer: bool = True,
    ) -> Any:
        try:
            resultat = self.serveur.call_tool(name, arguments or {}, session=session)
        except McpError:
            raise
        except Exception as e:
            raise McpError(f"Échec tools/call {name} sur {self.serveur.name} : {e}") from e

        if auditer and session is not None:
            resume = resultat if isinstance(resultat, dict) else {"resultat": str(resultat)[:200]}
            # Évite d'alourdir l'audit avec des payloads métier complets
            apercu = {
                cle: (valeur if not isinstance(valeur, list) else f"{len(valeur)} élément(s)")
                for cle, valeur in resume.items()
            } if isinstance(resume, dict) else resume
            tracer(
                session,
                acteur=f"systeme:mcp_client",
                acteur_type="agent",
                type="mcp_tools_call",
                objet=f"mcp:{self.serveur.name}/{name}",
                apres={
                    "protocole": "MCP",
                    "method": "tools/call",
                    "server": self.serveur.name,
                    "tool": name,
                    "resultat": apercu,
                },
                motif=f"Appel MCP tools/call `{name}`",
            )
        return resultat
