"""Protocole MCP minimal : discovery (tools/list) et invocation (tools/call)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class McpError(Exception):
    """Erreur protocole ou tool MCP."""


@dataclass(frozen=True)
class McpToolDef:
    name: str
    description: str
    input_schema: dict


ToolHandler = Callable[[dict, Any], Any]


class McpServerLocal:
    """Serveur MCP in-process (pas de réseau) pour la démo BDD / ERP."""

    def __init__(self, name: str, tools: dict[str, tuple[McpToolDef, ToolHandler]]):
        self.name = name
        self._tools = tools

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": definition.name,
                "description": definition.description,
                "inputSchema": definition.input_schema,
            }
            for definition, _ in self._tools.values()
        ]

    def call_tool(self, name: str, arguments: dict | None = None, *, session: Any = None) -> Any:
        if name not in self._tools:
            raise McpError(f"Tool MCP inconnu sur {self.name} : {name}")
        _definition, handler = self._tools[name]
        return handler(arguments or {}, session)
