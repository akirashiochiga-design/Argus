# Argus — hackathon

Plateforme SaaS pour créer, gouverner, exécuter et auditer des agents d'IA de
gestion de sinistres. Périmètre gelé : voir `CLAUDE.md`.

## Lancer (2 terminaux)

```sh
# 1. Backend — http://localhost:8000 (API docs : /docs)
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # 1re fois
.venv/Scripts/python -m app.seed                                        # reset démo
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

# 2. Frontend — http://localhost:5173
cd frontend
npm install        # 1re fois
npm run dev
```

Clé API : copier `backend/.env.example` vers `backend/.env` et renseigner
`ANTHROPIC_API_KEY`. **Sans clé, l'app fonctionne intégralement** : les agents
LLM basculent en mode simulation (badge « simulé » dans l'UI) ; avec la clé, ils
font de vrais appels Claude (texte + vision, badge « IA »).

**Modèle : `claude-haiku-4-5` par défaut** — le moins cher de l'API Anthropic,
vision comprise, ~1-2 cents par dossier. Les crédits offerts à l'inscription sur
console.anthropic.com couvrent tout le hackathon. Pour plus de qualité
rédactionnelle : `ARGUS_MODEL=claude-sonnet-5` ou `claude-opus-4-8` dans `.env`.

## Direction artistique

Interface alignée sur le brand book (`docs/Argus-Brand-Book.pdf`) : palette
encre `#17150F` / crème `#F4F1EA` / terracotta `#D97757` (accent unique), typo
Space Grotesk, signe « huit yeux » (favicon + header). Voix courte et chiffrée.

## Démo

Le script minuté, la checklist et le plan B sont dans **[docs/demo.md](docs/demo.md)**.

```sh
# Reset démo (entre deux répétitions) — remet les 3 dossiers calibrés à zéro
curl -X POST http://localhost:8000/admin/reseed

# Test de bout en bout (backend démarré) — 34 vérifications, doit tout passer
cd backend && .venv/Scripts/python test_e2e.py
```

Dossier vedette **SIN-2026-001** : facture 2 300 − vétusté 10 % − franchise 220
= **1 850 DT**, calculés en déterministe, validés par un humain, tracés dans l'audit.

## État d'avancement (plan CLAUDE.md §8)

- [x] 1. Squelette : FastAPI + SQLite + seed, React/Vite/Tailwind
- [x] 2. Pipeline backend : orchestrateur + 7 agents (montant 100 % déterministe)
- [x] 3. File d'approbation + audit append-only
- [x] 4. Studio (créer/publier/brancher/versionner) + vue pipeline animée
- [x] 5. Dashboard + journal d'audit + script de démo

Reste à faire par l'équipe : déposer de vraies photos de dégâts dans
`docs/samples/`, renseigner la clé API, et répéter avec `docs/demo.md`.
