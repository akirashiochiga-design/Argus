# Prompt de lancement — à coller dans Claude Code

> Place d'abord `CLAUDE.md` à la racine du dépôt et `cahier-des-charges.md`
> dans `docs/`. Lance `claude` depuis la racine, puis colle le message ci-dessous.

---

## Message d'ouverture (copier-coller)

Lis `CLAUDE.md` en entier, puis survole `docs/cahier-des-charges.md` (c'est la vision complète — PAS le périmètre du hackathon ; le périmètre gelé est dans CLAUDE.md section 2 et 3).

On est une équipe de 3, hackathon de 3 jours. Objectif de démo : faire tourner en direct un dossier de sinistre auto de la déclaration au règlement (le parcours P5 du cahier des charges), avec création d'un agent en live dans le studio.

Ne code rien pour l'instant. Je veux d'abord qu'on valide l'architecture ensemble. Propose-moi :

1. **L'arborescence du dépôt** (backend FastAPI, frontend React/Vite, docs, seed) — complète mais pas sur-ingéniérée.

2. **Le modèle de données** concret (SQLModel) à partir de la section 6 de CLAUDE.md. Montre les classes avec leurs champs.

3. **Le moteur d'orchestration** : comment un `Workflow` (liste d'étapes) fait avancer un `Dossier` d'agent en agent, où s'insèrent les nœuds human-in-the-loop, et comment chaque étape écrit un `Run` et un `EvenementAudit`. Décris-le comme une machine à états simple, en pseudo-code d'abord.

4. **Le contrat des 7 agents** : pour chacun, sa signature (entrées → sorties), et surtout lesquels appellent le LLM vs lesquels sont du code déterministe. Rappel non négociable : le calcul du montant (garanties + indemnité) est déterministe, jamais du LLM.

5. **Les endpoints API** minimaux dont le frontend a besoin (créer agent, lister dossiers, exécuter workflow sur un dossier, lister la file d'approbation, décider une tâche, lire le journal d'audit, lire les KPI du dashboard).

6. **Le plan de découpage en 3 personnes** aligné sur l'ordre de construction (section 8 de CLAUDE.md) : qui fait quoi, et quels sont les points d'intégration entre frontend et backend.

Tiens compte des contraintes : SQLite (pas de Postgres/Docker), orchestrateur maison (pas de LangGraph), déclenchement manuel en démo, tout doit rester démontrable à chaque étape. Présente ça de façon concise, on itère ensuite avant de générer le squelette.

---

## Ensuite (une fois l'archi validée)

- "Génère le squelette : structure des dossiers, FastAPI qui démarre avec un /health, React+Vite+Tailwind qui affiche une page vide, les modèles SQLModel, et `seed.py` avec le dataset de démo calibré de la section 7. Rien d'autre."
- "Implémente l'orchestrateur + les agents 4 (garanties) et 5 (calcul indemnité) en déterministe, testés sur le dossier de démo du seed. Montre-moi le montant calculé sur ce dossier."
- "Ajoute les agents LLM (FNOL, extraction, gravité, courrier). Mets les appels Claude derrière une petite couche `llm.py` avec la clé en variable d'env. Génère les emails/extractions en parallèle (asyncio) avec un état de progression."
- "Construis la file d'approbation côté API + les événements d'audit. L'humain approuve/modifie/refuse ; rien ne passe à 'réglé' sans action humaine."
- "Frontend : la vue Pipeline — une frise des étapes P5, le dossier qui avance nœud par nœud, chaque agent qui s'allume et montre sa sortie, les portes humaines en évidence."
- "Frontend : le Studio (créer un agent depuis un template en 5-6 champs) et le Dashboard + journal d'audit."

## Garde-fous à rappeler si Claude Code dérive

- "Rappel : c'est hors périmètre (CLAUDE.md section 3). Fais-en un stub/libellé 'à venir', ne le code pas."
- "Rappel : jamais de LLM sur le montant. Déterministe."
- "On gèle le scope. Fais tourner de bout en bout ce qu'on a avant d'ajouter quoi que ce soit."
