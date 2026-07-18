"""Les 7 agents du pipeline P5.

Interface uniforme : chaque module expose
    executer(agent: Agent, dossier: Dossier, session: Session) -> dict
Le dict de sorties est appliqué au dossier par l'orchestrateur, qui écrit
aussi le Run et l'événement d'audit — les agents n'y touchent pas.

LLM   : fnol, extraction, gravite (vision), courrier
CODE  : garanties, indemnite, hitl  — jamais de LLM sur une décision d'argent.
"""
from . import courrier, extraction, fnol, garanties, gravite, hitl, indemnite

DISPATCH = {
    "fnol": fnol.executer,
    "extraction": extraction.executer,
    "vision": gravite.executer,
    "garanties": garanties.executer,
    "indemnite": indemnite.executer,
    "hitl": hitl.executer,
    "courrier": courrier.executer,
}
