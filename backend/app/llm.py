"""Unique porte d'entrée vers l'API Anthropic.

- Clé lue depuis ANTHROPIC_API_KEY (via .env), jamais en dur.
- Sorties structurées garanties par `output_config.format` (json_schema).
- Si la clé est absente ou que l'appel échoue (réseau coupé en démo),
  l'appelant reçoit LLMIndisponible et bascule sur son fallback simulé :
  la démo ne peut pas planter.

Rappel non négociable : aucun montant de règlement ne sort d'ici.
Le LLM lit, structure, explique — le calcul d'argent est dans
agents/garanties.py et agents/indemnite.py (code pur).
"""
import base64
import json
import os
import time
from pathlib import Path
from typing import Optional

MODELE = os.environ.get("ARGUS_MODEL", "claude-opus-4-8")

# Prix $/MTok (claude-opus-4-8) pour le coût affiché au dashboard
PRIX_INPUT = 5.00 / 1_000_000
PRIX_OUTPUT = 25.00 / 1_000_000

# Racine du repo pour résoudre les chemins de pièces ("docs/samples/...")
RACINE = Path(__file__).resolve().parent.parent.parent


class LLMIndisponible(Exception):
    """Clé absente ou appel API en échec — l'agent doit utiliser son fallback."""


def cle_presente() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _bloc_image(chemin: Path) -> Optional[dict]:
    suffixe = chemin.suffix.lower()
    media = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(suffixe)
    if not media or not chemin.exists():
        return None
    data = base64.standard_b64encode(chemin.read_bytes()).decode("utf-8")
    return {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}}


def generer_json(
    system: str,
    texte_utilisateur: str,
    schema: dict,
    images: Optional[list[str]] = None,  # chemins relatifs à la racine du repo
    max_tokens: int = 4096,
) -> dict:
    """Appel Claude avec sortie JSON garantie par le schéma.

    Retourne {"donnees": <objet validé>, "cout": float, "duree_ms": int, "mode": "llm"}.
    Lève LLMIndisponible si pas de clé / erreur API.
    """
    if not cle_presente():
        raise LLMIndisponible("ANTHROPIC_API_KEY absente")

    import anthropic

    contenu: list[dict] = []
    for chemin in images or []:
        bloc = _bloc_image(RACINE / chemin)
        if bloc:
            contenu.append(bloc)
    contenu.append({"type": "text", "text": texte_utilisateur})

    t0 = time.monotonic()
    try:
        client = anthropic.Anthropic()
        reponse = client.messages.create(
            model=MODELE,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": contenu}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
    except anthropic.APIConnectionError as e:
        raise LLMIndisponible(f"connexion API impossible : {e}") from e
    except anthropic.APIStatusError as e:
        raise LLMIndisponible(f"erreur API {e.status_code} : {e.message}") from e

    duree_ms = int((time.monotonic() - t0) * 1000)
    texte = next(b.text for b in reponse.content if b.type == "text")
    cout = reponse.usage.input_tokens * PRIX_INPUT + reponse.usage.output_tokens * PRIX_OUTPUT
    return {"donnees": json.loads(texte), "cout": round(cout, 6), "duree_ms": duree_ms, "mode": "llm"}


def generer_texte(system: str, texte_utilisateur: str, max_tokens: int = 4096) -> dict:
    """Appel Claude en texte libre (agent courrier)."""
    if not cle_presente():
        raise LLMIndisponible("ANTHROPIC_API_KEY absente")

    import anthropic

    t0 = time.monotonic()
    try:
        client = anthropic.Anthropic()
        reponse = client.messages.create(
            model=MODELE,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": texte_utilisateur}],
        )
    except anthropic.APIConnectionError as e:
        raise LLMIndisponible(f"connexion API impossible : {e}") from e
    except anthropic.APIStatusError as e:
        raise LLMIndisponible(f"erreur API {e.status_code} : {e.message}") from e

    duree_ms = int((time.monotonic() - t0) * 1000)
    texte = next(b.text for b in reponse.content if b.type == "text")
    cout = reponse.usage.input_tokens * PRIX_INPUT + reponse.usage.output_tokens * PRIX_OUTPUT
    return {"texte": texte, "cout": round(cout, 6), "duree_ms": duree_ms, "mode": "llm"}
