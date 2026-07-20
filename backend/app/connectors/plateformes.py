"""Catalogue de plateformes MCP (style console Anthropic) — connexions simulées."""
from __future__ import annotations

from datetime import datetime, timezone


# Catalogue fermé : la démo montre le modèle « connecter une app à un agent via MCP ».
# Aucun OAuth réel : connecter = activer le pack de tools + audit.
PLATEFORMES_MCP: list[dict] = [
    {
        "slug": "gmail",
        "nom": "Gmail",
        "editeur": "Google",
        "categorie": "Messagerie",
        "description": "Lire et préparer des e-mails (envoi soumis à validation humaine).",
        "couleur": "#EA4335",
        "initiales": "GM",
        "tools": ["lister_emails", "lire_email", "preparer_brouillon"],
    },
    {
        "slug": "outlook",
        "nom": "Outlook",
        "editeur": "Microsoft",
        "categorie": "Messagerie",
        "description": "Boîte mail entreprise et calendrier Outlook.",
        "couleur": "#0078D4",
        "initiales": "OL",
        "tools": ["lister_emails", "lire_email", "lister_evenements"],
    },
    {
        "slug": "slack",
        "nom": "Slack",
        "editeur": "Salesforce",
        "categorie": "Collaboration",
        "description": "Notifier un canal ou récupérer le contexte d'un fil.",
        "couleur": "#4A154B",
        "initiales": "SL",
        "tools": ["poster_message", "lire_canal", "lister_canaux"],
    },
    {
        "slug": "teams",
        "nom": "Microsoft Teams",
        "editeur": "Microsoft",
        "categorie": "Collaboration",
        "description": "Messages d'équipe et canaux Teams.",
        "couleur": "#6264A7",
        "initiales": "TM",
        "tools": ["poster_message", "lire_canal"],
    },
    {
        "slug": "whatsapp_business",
        "nom": "WhatsApp Business",
        "editeur": "Meta",
        "categorie": "Messagerie",
        "description": "Messages template vers l'assuré (opt-in requis).",
        "couleur": "#25D366",
        "initiales": "WA",
        "tools": ["envoyer_template", "lire_conversation"],
    },
    {
        "slug": "google_drive",
        "nom": "Google Drive",
        "editeur": "Google",
        "categorie": "Documents",
        "description": "Lister et lire des pièces jointes sinistre.",
        "couleur": "#4285F4",
        "initiales": "GD",
        "tools": ["lister_fichiers", "lire_fichier"],
    },
    {
        "slug": "onedrive",
        "nom": "OneDrive",
        "editeur": "Microsoft",
        "categorie": "Documents",
        "description": "Documents SharePoint / OneDrive de l'assureur.",
        "couleur": "#094AB2",
        "initiales": "OD",
        "tools": ["lister_fichiers", "lire_fichier"],
    },
    {
        "slug": "notion",
        "nom": "Notion",
        "editeur": "Notion",
        "categorie": "Knowledge",
        "description": "Base documentaire interne (procédures, barèmes).",
        "couleur": "#000000",
        "initiales": "NO",
        "tools": ["chercher_pages", "lire_page"],
    },
]


def catalogue() -> list[dict]:
    return [
        {
            **plateforme,
            "protocole": "MCP",
            "mode": "simulation",
            "tools_count": len(plateforme["tools"]),
        }
        for plateforme in PLATEFORMES_MCP
    ]


def obtenir(slug: str) -> dict:
    for plateforme in PLATEFORMES_MCP:
        if plateforme["slug"] == slug:
            return plateforme
    raise KeyError(f"Plateforme MCP inconnue : {slug}")


def compte_demo(slug: str) -> str:
    demos = {
        "gmail": "sinistres@compagnie.tn",
        "outlook": "ops@compagnie.tn",
        "slack": "#sinistres-auto",
        "teams": "Équipe Sinistres",
        "whatsapp_business": "+216 70 000 000",
        "google_drive": "Drive / Sinistres 2026",
        "onedrive": "OneDrive / Pièces",
        "notion": "Wiki procédures",
    }
    return demos.get(slug, "compte-demo")


def connexion_active(agent_garde_fous: dict, slug: str) -> dict | None:
    connexions = (agent_garde_fous or {}).get("connexions_mcp") or {}
    return connexions.get(slug)


def connecter(agent_garde_fous: dict, slug: str) -> dict:
    plateforme = obtenir(slug)
    connexions = dict((agent_garde_fous or {}).get("connexions_mcp") or {})
    connexions[slug] = {
        "statut": "connecte",
        "protocole": "MCP",
        "compte": compte_demo(slug),
        "tools": plateforme["tools"],
        "connecte_le": datetime.now(timezone.utc).isoformat(),
        "simulation": True,
    }
    return {**(agent_garde_fous or {}), "connexions_mcp": connexions}


def deconnecter(agent_garde_fous: dict, slug: str) -> dict:
    obtenir(slug)  # valide le slug
    connexions = dict((agent_garde_fous or {}).get("connexions_mcp") or {})
    connexions.pop(slug, None)
    return {**(agent_garde_fous or {}), "connexions_mcp": connexions}
