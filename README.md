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
`ANTHROPIC_API_KEY` (nécessaire à partir de l'étape 3 — agents LLM).

## Reset démo

`python -m app.seed` supprime et recrée `backend/argus.db` avec le dataset
calibré : 6 polices, 7 agents, le workflow P5, 3 dossiers dont **SIN-2026-001**
(2 300 − vétusté 10 % − franchise 220 = **1 850 DT**).

## État d'avancement (plan CLAUDE.md §8)

- [x] 1. Squelette : FastAPI + SQLite + seed, React/Vite/Tailwind, 4 écrans en coquille
- [ ] 2. Pipeline backend : orchestrateur + 7 agents (montant déterministe)
- [ ] 3. File d'approbation + audit
- [ ] 4. Studio + vue pipeline animée
- [ ] 5. Dashboard + polish
