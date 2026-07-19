"""Porte d'entrée unique vers Gemini, avec Anthropic en secours.

- Gemini est sélectionné dès que GEMINI_API_KEY est présente.
- Anthropic reste disponible pour les environnements existants.
- Les clés sont lues depuis l'environnement, jamais en dur.
- Si la clé est absente ou que l'appel échoue (réseau coupé en démo),
  l'appelant reçoit LLMIndisponible et bascule sur son fallback :
  le parcours ne peut pas planter.

Rappel non négociable : aucun montant de règlement ne sort d'ici.
Le LLM lit, structure, explique — le calcul d'argent est dans
agents/garanties.py et agents/indemnite.py (code pur).
"""
import base64
import json
import os
import time
from pathlib import Path
from typing import Callable, Optional

# Haiku 4.5 par défaut : le moins cher de l'API Anthropic (~1-2 cents/dossier,
# vision comprise). Monter en gamme via ARGUS_MODEL=claude-sonnet-5 ou claude-opus-4-8.
MODELE = os.environ.get("ARGUS_MODEL", "claude-haiku-4-5")
MODELE_GEMINI_DEFAUT = "gemini-2.5-flash"

# Prix $/MTok (input, output) pour le coût affiché au dashboard
PRIX_PAR_MODELE = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-opus-4-8": (5.00, 25.00),
}
_prix = next((p for m, p in PRIX_PAR_MODELE.items() if MODELE.startswith(m)), (5.00, 25.00))
PRIX_INPUT = _prix[0] / 1_000_000
PRIX_OUTPUT = _prix[1] / 1_000_000

# Racine du repo pour résoudre les chemins de pièces ("docs/samples/...")
RACINE = Path(__file__).resolve().parent.parent.parent


class LLMIndisponible(Exception):
    """Clé absente ou appel API en échec — l'agent doit utiliser son fallback."""


def fournisseur() -> str:
    """Retourne le fournisseur configuré, Gemini étant prioritaire."""
    force = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if force in {"gemini", "anthropic"}:
        return force
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "gemini"


def cle_presente() -> bool:
    variable = "GEMINI_API_KEY" if fournisseur() == "gemini" else "ANTHROPIC_API_KEY"
    return bool(os.environ.get(variable))


def _bloc_image(chemin: Path) -> Optional[dict]:
    suffixe = chemin.suffix.lower()
    media = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(suffixe)
    if not media or not chemin.exists():
        return None
    data = base64.standard_b64encode(chemin.read_bytes()).decode("utf-8")
    return {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}}


def _parties_gemini(texte: str, images: Optional[list[str]] = None) -> list:
    from google.genai import types

    parties = []
    medias = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    for chemin_relatif in images or []:
        chemin = RACINE / chemin_relatif
        media = medias.get(chemin.suffix.lower())
        if media and chemin.exists():
            parties.append(types.Part.from_bytes(data=chemin.read_bytes(), mime_type=media))
    parties.append(types.Part.from_text(text=texte))
    return parties


def _client_gemini():
    try:
        from google import genai
    except ImportError as e:
        raise LLMIndisponible("dépendance google-genai absente") from e
    return genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


def _modele_gemini() -> str:
    return os.environ.get("GEMINI_MODEL", MODELE_GEMINI_DEFAUT)


def _reflexion_gemini():
    """Réserve les tokens à la réponse pour les modèles Gemini 3."""
    if not _modele_gemini().startswith("gemini-3"):
        return None
    from google.genai import types

    return types.ThinkingConfig(thinking_level="MINIMAL")


def _cout_gemini(reponse) -> float:
    """Coût configurable, nul par défaut pour le quota gratuit Gemini."""
    usage = getattr(reponse, "usage_metadata", None)
    tokens_entree = getattr(usage, "prompt_token_count", 0) or 0
    tokens_sortie = getattr(usage, "candidates_token_count", 0) or 0
    prix_entree = float(os.environ.get("GEMINI_INPUT_USD_MTOK", "0"))
    prix_sortie = float(os.environ.get("GEMINI_OUTPUT_USD_MTOK", "0"))
    return (tokens_entree * prix_entree + tokens_sortie * prix_sortie) / 1_000_000


def _gemini_json(
    system: str,
    texte_utilisateur: str,
    schema: dict,
    images: Optional[list[str]],
    max_tokens: int,
) -> dict:
    from google.genai import types

    t0 = time.monotonic()
    client = _client_gemini()
    try:
        reponse = client.models.generate_content(
            model=_modele_gemini(),
            contents=_parties_gemini(texte_utilisateur, images),
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
                response_json_schema=schema,
                thinking_config=_reflexion_gemini(),
            ),
        )
        donnees = json.loads(reponse.text)
    except LLMIndisponible:
        raise
    except Exception as e:
        raise LLMIndisponible(f"erreur API Gemini : {e}") from e
    return {
        "donnees": donnees,
        "cout": round(_cout_gemini(reponse), 6),
        "duree_ms": int((time.monotonic() - t0) * 1000),
        "mode": "llm",
    }


def _gemini_json_avec_outils(
    system: str,
    texte_utilisateur: str,
    schema: dict,
    outils: list[dict],
    executer_outil: Callable[[str, dict], dict],
    images: Optional[list[str]],
    max_tokens: int,
) -> dict:
    """Consulte les outils, puis produit une sortie structurée séparément."""
    from google.genai import types

    declarations = [
        types.FunctionDeclaration(
            name=outil["name"],
            description=outil.get("description"),
            parameters_json_schema=outil.get("input_schema", {"type": "object"}),
        )
        for outil in outils
    ]
    t0 = time.monotonic()
    client = _client_gemini()
    try:
        reponse_outils = client.models.generate_content(
            model=_modele_gemini(),
            contents=_parties_gemini(
                texte_utilisateur
                + "\nConsulte toutes les sources utiles maintenant, en parallèle si nécessaire.",
                images,
            ),
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                tools=[types.Tool(function_declarations=declarations)],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(mode="ANY")
                ),
                thinking_config=_reflexion_gemini(),
            ),
        )
    except Exception as e:
        raise LLMIndisponible(f"erreur API Gemini : {e}") from e

    appels = list(reponse_outils.function_calls or [])
    if not appels:
        raise LLMIndisponible("réponse Gemini sans appel d'outil")

    actions = []
    sources = []
    for appel in appels:
        entree = dict(appel.args or {})
        debut_outil = time.monotonic()
        try:
            resultat = executer_outil(appel.name, entree)
            statut = "succes"
        except Exception as e:
            resultat = {"erreur": str(e)}
            statut = "refuse"
        actions.append({
            "ordre": len(actions) + 1,
            "type": "outil",
            "outil": appel.name,
            "entree": entree,
            "resultat": resultat,
            "statut": statut,
            "duree_ms": int((time.monotonic() - debut_outil) * 1000),
        })
        sources.append({"outil": appel.name, "resultat": resultat})

    prompt_final = (
        f"{texte_utilisateur}\n\n"
        "Sources métier consultées par l'agent :\n"
        f"{json.dumps(sources, ensure_ascii=False)}\n\n"
        "Produis maintenant la réponse finale en t'appuyant sur ces sources."
    )
    try:
        reponse_finale = client.models.generate_content(
            model=_modele_gemini(),
            contents=_parties_gemini(prompt_final, images),
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
                response_json_schema=schema,
                thinking_config=_reflexion_gemini(),
            ),
        )
        donnees = json.loads(reponse_finale.text)
    except Exception as e:
        raise LLMIndisponible(f"erreur API Gemini : {e}") from e

    return {
        "donnees": donnees,
        "cout": round(_cout_gemini(reponse_outils) + _cout_gemini(reponse_finale), 6),
        "duree_ms": int((time.monotonic() - t0) * 1000),
        "mode": "agent_outille",
        "iterations": 2,
        "actions": actions,
    }


def _gemini_texte(system: str, texte_utilisateur: str, max_tokens: int) -> dict:
    from google.genai import types

    t0 = time.monotonic()
    client = _client_gemini()
    try:
        reponse = client.models.generate_content(
            model=_modele_gemini(),
            contents=texte_utilisateur,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                thinking_config=_reflexion_gemini(),
            ),
        )
        texte = reponse.text
    except LLMIndisponible:
        raise
    except Exception as e:
        raise LLMIndisponible(f"erreur API Gemini : {e}") from e
    return {
        "texte": texte,
        "cout": round(_cout_gemini(reponse), 6),
        "duree_ms": int((time.monotonic() - t0) * 1000),
        "mode": "llm",
    }


def generer_json(
    system: str,
    texte_utilisateur: str,
    schema: dict,
    images: Optional[list[str]] = None,  # chemins relatifs à la racine du repo
    max_tokens: int = 4096,
) -> dict:
    """Appel LLM avec sortie JSON garantie par le schéma.

    Retourne {"donnees": <objet validé>, "cout": float, "duree_ms": int, "mode": "llm"}.
    Lève LLMIndisponible si pas de clé / erreur API.
    """
    if not cle_presente():
        variable = "GEMINI_API_KEY" if fournisseur() == "gemini" else "ANTHROPIC_API_KEY"
        raise LLMIndisponible(f"{variable} absente")
    if fournisseur() == "gemini":
        return _gemini_json(system, texte_utilisateur, schema, images, max_tokens)

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


def generer_json_avec_outils(
    system: str,
    texte_utilisateur: str,
    schema: dict,
    outils: list[dict],
    executer_outil: Callable[[str, dict], dict],
    images: Optional[list[str]] = None,
    max_iterations: int = 4,
    max_tokens: int = 4096,
) -> dict:
    """Boucle agentique avec outils contrôlés et sortie structurée.

    Les handlers sont fournis par l'appelant et restent la seule frontière
    d'exécution. Une boucle trop longue ou une erreur API déclenche le fallback
    de l'agent via LLMIndisponible.
    """
    if not outils:
        raise ValueError("Un agent outillé doit disposer d'au moins un outil")
    if max_iterations < 2:
        raise ValueError("max_iterations doit permettre un appel outil puis une réponse")
    if not cle_presente():
        variable = "GEMINI_API_KEY" if fournisseur() == "gemini" else "ANTHROPIC_API_KEY"
        raise LLMIndisponible(f"{variable} absente")
    if fournisseur() == "gemini":
        return _gemini_json_avec_outils(
            system,
            texte_utilisateur,
            schema,
            outils,
            executer_outil,
            images,
            max_tokens,
        )

    import anthropic

    contenu: list[dict] = []
    for chemin in images or []:
        bloc = _bloc_image(RACINE / chemin)
        if bloc:
            contenu.append(bloc)
    contenu.append({"type": "text", "text": texte_utilisateur})
    messages: list[dict] = [{"role": "user", "content": contenu}]

    actions: list[dict] = []
    cout_total = 0.0
    t0 = time.monotonic()
    client = anthropic.Anthropic()

    for iteration in range(1, max_iterations + 1):
        try:
            reponse = client.messages.create(
                model=MODELE,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                tools=outils,
                # Le premier tour doit consulter au moins une source métier.
                tool_choice={"type": "any"} if iteration == 1 else {"type": "auto"},
                output_config={"format": {"type": "json_schema", "schema": schema}},
            )
        except anthropic.APIConnectionError as e:
            raise LLMIndisponible(f"connexion API impossible : {e}") from e
        except anthropic.APIStatusError as e:
            raise LLMIndisponible(f"erreur API {e.status_code} : {e.message}") from e

        cout_total += (
            reponse.usage.input_tokens * PRIX_INPUT
            + reponse.usage.output_tokens * PRIX_OUTPUT
        )
        appels = [bloc for bloc in reponse.content if bloc.type == "tool_use"]
        if not appels:
            bloc_texte = next((bloc for bloc in reponse.content if bloc.type == "text"), None)
            if not bloc_texte:
                raise LLMIndisponible("réponse agent sans sortie structurée")
            try:
                donnees = json.loads(bloc_texte.text)
            except json.JSONDecodeError as e:
                raise LLMIndisponible("sortie agent non conforme au schéma JSON") from e
            return {
                "donnees": donnees,
                "cout": round(cout_total, 6),
                "duree_ms": int((time.monotonic() - t0) * 1000),
                "mode": "agent_outille",
                "iterations": iteration,
                "actions": actions,
            }

        messages.append({
            "role": "assistant",
            "content": [bloc.model_dump(exclude_none=True) for bloc in reponse.content],
        })
        resultats_outils = []
        for bloc in appels:
            debut_outil = time.monotonic()
            try:
                resultat = executer_outil(bloc.name, dict(bloc.input or {}))
                statut = "succes"
                est_erreur = False
            except Exception as e:
                resultat = {"erreur": str(e)}
                statut = "refuse"
                est_erreur = True
            actions.append({
                "ordre": len(actions) + 1,
                "type": "outil",
                "outil": bloc.name,
                "entree": dict(bloc.input or {}),
                "resultat": resultat,
                "statut": statut,
                "duree_ms": int((time.monotonic() - debut_outil) * 1000),
            })
            resultats_outils.append({
                "type": "tool_result",
                "tool_use_id": bloc.id,
                "content": json.dumps(resultat, ensure_ascii=False),
                "is_error": est_erreur,
            })
        messages.append({"role": "user", "content": resultats_outils})

    raise LLMIndisponible(f"limite de {max_iterations} itérations atteinte")


def generer_texte(system: str, texte_utilisateur: str, max_tokens: int = 4096) -> dict:
    """Appel LLM en texte libre (agent courrier)."""
    if not cle_presente():
        variable = "GEMINI_API_KEY" if fournisseur() == "gemini" else "ANTHROPIC_API_KEY"
        raise LLMIndisponible(f"{variable} absente")
    if fournisseur() == "gemini":
        return _gemini_texte(system, texte_utilisateur, max_tokens)

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
