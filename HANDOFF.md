# HANDOFF — Argus (hackathon)

> Document de reprise pour continuer ce projet dans une **nouvelle session Claude**
> (limite de tokens atteinte, changement de machine, etc.). Lis ce fichier en
> entier, puis `CLAUDE.md` (source de vérité produit/scope), puis lance la
> checklist de vérification en bas de page avant de coder quoi que ce soit.

Dernière mise à jour : 2026-07-18 (fin de session, tout committé, tout vert).

---

## 1. En une phrase

Argus est une plateforme SaaS B2B qui permet à un assureur de **créer,
déployer, exploiter et auditer des agents d'IA** pour la gestion des
sinistres auto, avec un principe non négociable : **le LLM lit et explique,
le code calcule, l'humain décide de l'argent, tout est tracé.**

Hackathon 3 jours, équipe de 3. Le scope gelé est dans `CLAUDE.md` — **ce
fichier prime sur tout**. Ne pas construire hors de ce périmètre sans
validation explicite de l'utilisateur.

## 2. État du projet : tout est fonctionnel

Les 5 étapes du plan (`CLAUDE.md` §8) sont terminées. `backend/test_e2e.py`
contenait 47 vérifications automatiques — **actuellement cassé** depuis le
commit "Supprime les dossiers fictifs du jeu de données initial" (2026-07-19) :
`/admin/reseed` ne crée plus les dossiers `SIN-2026-00x` sur lesquels le
script se base. Le reset crée maintenant des dossiers via la synchro
CoreSinistre (`EXT-SIN-2026-1002`/`1003`), fonctionnels bout-en-bout, mais
`test_e2e.py` n'a pas encore été remis à jour pour matcher. Ne pas se fier à
ce script tel quel comme preuve que la démo marche — vérifier manuellement
(`POST /admin/reseed` puis dérouler un dossier dans l'UI).

```sh
cd backend
.venv/Scripts/python -m uvicorn app.main:app --port 8001   # terminal 1
# terminal 2, backend démarré :
.venv/Scripts/python test_e2e.py
```
Si ce script affiche `TOUS LES TESTS PASSENT`, l'app est démontrable.
`docs/demo.md` contient le script de démo minuté à suivre pour la présentation.

## 3. Comment démarrer (commandes exactes)

```sh
# Backend — http://localhost:8001 (docs OpenAPI sur /docs)
cd backend
.venv/Scripts/pip install -r requirements.txt   # si venv pas encore créé
.venv/Scripts/python -m app.seed                 # ou POST /admin/reseed une fois lancé
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8001

# Frontend — http://localhost:5173
cd frontend
npm install
npm run dev
```

Reset démo à tout moment : bouton **↻ Reset démo** dans le header, ou
`curl -X POST http://localhost:8001/admin/reseed`.

## 4. Arborescence (exacte, vérifiée à l'instant)

```
backend/
  app/
    main.py            FastAPI + CORS + montage des routers
    db.py               engine SQLite, session
    models.py            8 entités SQLModel (Template, Agent, Workflow, Police,
                         Dossier, Run, Tache, EvenementAudit)
    seed.py              dataset de démo calibré + reset ("python -m app.seed")
    samples.py            génère les documents/croquis d'exemple (docs/samples/)
    llm.py               UNIQUE porte vers l'API Anthropic (texte + vision)
    orchestrator.py       machine à états : avancer(), reculer(), rejouer(),
                          decider() — voir §6
    audit.py              helper unique d'écriture de la piste d'audit
    agents/               les 7 agents du pipeline P5 (voir §7)
      fnol.py extraction.py gravite.py            → LLM (avec fallback déterministe)
      garanties.py indemnite.py hitl.py           → déterministe, PAS de LLM
      courrier.py                                  → LLM (avec fallback déterministe)
    routers/
      dossiers.py    GET/POST /dossiers, /executer, /reculer, /rejouer
      taches.py      GET /taches, POST /taches/{id}/decider
      agents.py      studio : templates, agents, /workflows/{id}/ajouter-etape,
                     /studio/categories, /studio/generer-instructions,
                     /studio/agents-personnalises
      audit.py       GET /audit
      dashboard.py   GET /dashboard/kpi
      admin.py       POST /admin/reseed
  test_e2e.py          47 vérifications, rejouable avant chaque répétition
  .env.example         ANTHROPIC_API_KEY + ARGUS_MODEL (voir §8)

frontend/src/
  App.jsx              shell : gate de connexion, nav, reset démo, header
  session.js           authentification factice (localStorage) — voir §9
  api.js               UNIQUE point de contact avec le backend
  ui.jsx               Logo (signe brand book), Wordmark, badges, formatage
  pages/
    Login.jsx          écran de connexion
    Pipeline.jsx        frise animée, exécution pas-à-pas, reculer/rejouer,
                        déclaration + stub e-constat FTUSA
    Approbations.jsx     file HITL : approuver/modifier/refuser/sans_suite
    Studio.jsx           templates, agent perso par prompt, ajouter au pipeline,
                        éditer les instructions d'un agent de base
    Dashboard.jsx        KPI + journal d'audit filtrable

docs/
  demo.md                script de démo minuté, checklist, plan B, Q&A jury
  samples/                factures/devis/constat générés + croquis de dégâts
  Argus-Brand-Book.pdf / .html   direction artistique (source de vérité DA)
  cahier-des-charges.pdf / -condense.md   la VISION complète (pas le scope)
```

## 5. Modèle de données — rien à changer ici sans relire CLAUDE.md §6

`Dossier.etat` ∈ `{recu, en_cours, attente_validation, regle, refuse, cloture}`
— cette liste est intentionnellement plus courte que celle du cahier des
charges complet (qui a aussi `en_exception`). **Ne pas ajouter d'état sans
recréer un vrai besoin** — `cloture` sert déjà pour "assuré non-répondant"
(voir §7).

`Tache.type` ∈ `{validation_reglement, validation_refus, demande_piece}`.
`Tache.decision` ∈ `{approuver, modifier, refuser, sans_suite}` (validées dans
`orchestrator.decider()`).

## 6. L'orchestrateur — comment le pipeline avance

Machine à états pas-à-pas dans `orchestrator.py` :

- **`avancer(session, dossier)`** — exécute UNE étape (`workflow.etapes[dossier.etape_courante]`),
  écrit un `Run` + un événement d'audit, applique les sorties de l'agent aux
  champs du dossier (liste `CHAMPS_DOSSIER`), avance le curseur. S'arrête et
  retourne `resultat: "porte_humaine"` sur la porte HITL — **c'est le
  frontend qui boucle les appels** (`Pipeline.jsx`), pas le backend.
- **`reculer(session, dossier)`** — supprime le dernier `Run`, **reconstruit**
  l'état des champs du dossier à partir des runs restants (pas un undo
  champ par champ), décrémente le curseur. Si l'étape annulée était la porte
  humaine, supprime aussi la `Tache` associée.
- **`rejouer`** = `reculer` en boucle jusqu'à l'étape 0 (exposé côté router
  `dossiers.py`, pas dans l'orchestrateur lui-même).
- **`decider(session, tache, decision, validateur, montant, motif)`** — LE
  seul chemin vers `montant_valide`. `_etat_final()` détermine l'état
  terminal à partir de la décision humaine, **jamais** d'un agent.

⚠️ **Piège déjà rencontré deux fois dans cette session** : après
`session.commit()`, un objet SQLModel ajouté plus tôt dans la même fonction
(mais jamais explicitement `refresh`) redevient "expiré" et son
`.model_dump()` renvoie des champs vides. Le correctif est systématique :
`session.refresh(obj)` juste avant de sérialiser. Si un nouvel endpoint
renvoie un objet fraîchement créé/modifié et que des champs semblent vides
côté client, **c'est presque toujours ça** — chercher un `refresh` manquant
avant de chercher ailleurs.

## 7. Les 7 agents + la capacité d'adaptation

| # | Agent | Fichier | Nature |
|---|-------|---------|--------|
| 1 | FNOL | `agents/fnol.py` | LLM texte, repli heuristique par mots-clés |
| 2 | Extraction docs | `agents/extraction.py` | LLM vision, 1 appel/pièce, repli sur montant déclaré |
| 3 | Gravité vision | `agents/gravite.py` | LLM vision, repli texte si pas de photo/clé |
| 4 | Moteur de garanties | `agents/garanties.py` | **100% déterministe**, aucun appel LLM |
| 5 | Calcul indemnité | `agents/indemnite.py` | **100% déterministe**, aucun appel LLM |
| 6 | Porte HITL | `agents/hitl.py` | déterministe, non désactivable |
| 7 | Courrier | `agents/courrier.py` | LLM texte, repli lettre à trous |

Interface uniforme : `executer(agent, dossier, session) -> dict`. Le dict
de sorties est appliqué par l'orchestrateur (jamais par l'agent lui-même).

**Capacité d'adaptation (ajoutée en fin de session)** : si l'agent 5 ne
trouve aucune pièce chiffrée (`dossier.montant_estime is None`), il retourne
`recommandation: "demande_piece"` au lieu d'un montant à 0. L'agent 6 (hitl)
détecte ça via `_derniere_recommandation()` et crée une `Tache` de type
`demande_piece` — la file d'approbation affiche alors une carte dédiée avec
trois actions réelles :
- **📧 Relancer l'assuré** (`POST /taches/{id}/relancer`, `orchestrator.relancer()`)
  — envoie un email de relance (LLM ou repli déterministe, même pattern que
  `courrier.py`), l'ajoute à l'historique `Tache.relances` (append, jamais
  écrasé), trace un événement `relance_assure`. Ne décide rien : la tâche
  reste `en_attente`, on peut relancer plusieurs fois.
- **✎ Pièce reçue** (décision `modifier`, montant saisi manuellement → `réglé`).
- **🚫 Clôturer sans suite** (décision `sans_suite`, motif obligatoire →
  dossier `cloture`, lettre de clôture dédiée générée par `courrier.py`).
  Le motif se pré-remplit automatiquement avec la date de la dernière
  relance envoyée (`ouvrirClotureSansSuite()` dans `Approbations.jsx`),
  pour que la clôture référence toujours la tentative de relance.

C'est la traduction "hackathon-démontrable" de *"relance email au bout d'un
certain temps sans réponse"* : comme un vrai délai ne peut pas s'écouler en
direct pendant une démo, le geste (relancer, puis constater l'absence de
réponse, puis clôturer en le citant) reste manuel mais réel — rien n'est
préfabriqué, l'email est vraiment généré et vraiment tracé.

Le dossier seed `SIN-2026-004` (police couverte, aucune pièce chiffrée
jointe) est laissé à l'état `recu` pour démontrer cette porte en direct
pendant la démo — ne pas l'exécuter dans le seed lui-même, ça casserait la
mise en scène.

## 8. LLM — modèle et clé API

`llm.py` est l'unique point d'appel Anthropic. **Modèle par défaut :
`claude-haiku-4-5`** (le moins cher de l'API, vision comprise, ~1-2 cents
par dossier complet) — changeable via `ARGUS_MODEL` dans `.env`
(`claude-sonnet-5` ou `claude-opus-4-8` pour plus de qualité rédactionnelle).

**Clé API branchée** : la clé est configurée dans `backend/.env`
(variable `ANTHROPIC_API_KEY`). Les agents LLM appelent réellement l'API
Anthropic et produisent des sorties avec `mode: "llm"`, affichées avec le
badge terracotta "IA" dans l'UI. Le coût de chaque appel est calculé et
affiché dans le dashboard (`cout_ia_usd`).

**Robustesse via fallbacks** : chaque agent LLM a un repli déterministe/
heuristique (voir tableau §7), utilisé seulement si l'API est indisponible
ou si la clé n'est pas configurée. C'est un choix de robustesse : la démo ne
plante pas si le Wi-Fi tombe, mais en conditions normales tous les agents
LLM appellent l'API et retournent des résultats réels.

Les **croquis d'expertise générés** (`backend/app/samples.py` → vue de
dessus du véhicule, zone endommagée hachurée) tiennent lieu de photos dans
`docs/samples/` (`degats-1/2/3.jpg`, `parebrise.jpg`), référencés dans
`seed.py`. Avec la clé API, `gravite.py` envoie réellement ces images à
Claude (vision) pour une analyse authentique.

## 9. Authentification (factice, assumée)

`CLAUDE.md` §3 : *"RBAC fin [hors scope]. Un login factice + un rôle
'superviseur' suffisent."* — `frontend/src/session.js` implémente
exactement ça, purement côté client (localStorage, aucun endpoint
backend) :
- Compte de démo affiché en clair sur l'écran de connexion :
  `selma.gharbi@argus-demo.tn` / `argus2026` → identité soignée "Selma
  Gharbi (superviseure)".
- **N'importe quel autre email/mot de passe est aussi accepté** (stub
  assumé) — le nom affiché est dérivé de l'email saisi
  (`ahmed.ben.salah@x.tn` → "Ahmed Ben Salah"). L'identité connectée est
  celle qui apparaît partout : header, "décideur" de la file d'approbation,
  et surtout la piste d'audit (`humain:<nom> (<rôle>)`).
- Ne PAS construire de vrai backend d'auth (JWT, hash de mot de passe,
  table Utilisateur) sans une demande explicite — c'est hors scope gelé.

## 10. Direction artistique — brand book, à respecter strictement

Palette : **encre `#17150F`** (texte/fonds sombres), **crème `#F4F1EA`**
(fond de page), **terracotta `#D97757`** (accent, **un seul par écran**,
jamais deux). Typo **Space Grotesk** (Google Fonts, chargée dans
`index.css`). Wordmark `argus.` bas de casse, point terracotta. Voix :
phrases courtes, chiffres plutôt qu'adjectifs, jamais "révolutionnaire"/
"disruptif"/"puissant" (voir `docs/Argus-Brand-Book.html` §04).

**Le signe** (« huit yeux, un seul regard ») a un tracé SVG exact — ne pas
improviser une nouvelle géométrie. Il est défini dans `ui.jsx` :
```
PETALE = 'M120 107 Q101 66 120 25 Q139 66 120 107 Z'
```
répété à `rotate(0,45,90,...,315)` autour de `(120,120)`, viewBox
`0 0 240 240`, `stroke-width 8`, pupille `<circle r="13" fill="#D97757">`.
Même géométrie dans `frontend/public/favicon.svg`. **Si le signe doit être
retouché, extraire le tracé exact du brand book HTML (`docs/Argus-Brand-
Book.html`, `<symbol id="argusmark">`), ne pas en redessiner un
approximatif** — erreur déjà commise une fois dans cette session, corrigée
ensuite.

## 11. Hors scope — assumé, à ne PAS construire sans validation

Ces sujets ont été demandés pendant la session ; réponse donnée = explication
+ stub honnête, PAS d'implémentation réelle. Ne pas revenir dessus sans que
l'utilisateur le redemande explicitement :

- **Connecteur e-constat FTUSA réel** — aucune API publique/credentials
  connus. Un bouton *« Récupérer via e-constat FTUSA »* dans
  `Pipeline.jsx` (formulaire de déclaration) simule le pré-remplissage
  (clairement étiqueté "connecteur simulé"), sans aucun appel réseau. Si un
  jour une vraie API FTUSA est fournie avec des credentials, le point
  d'intégration serait `POST /dossiers` côté backend : un nouvel endpoint
  `POST /connecteurs/e-constat/{ref}` qui interroge l'API réelle et retourne
  une déclaration structurée, appelé depuis ce même bouton frontend.
- **Connecteurs ERP réels des compagnies** — `CLAUDE.md` §3 l'exclut
  explicitement ("Tout est simulé par des données locales"). Le point
  d'architecture pour en discuter au pitch (roadmap, pas à coder) :
  1. Une entité `Connecteur` (nom, type d'ERP, credentials chiffrés, mapping
     de champs) — présente dans le modèle complet du cahier des charges
     (M8.3) mais absente du modèle réduit du hackathon.
  2. Un point d'écriture sortant : quand `Dossier.etat` passe à `regle`,
     un job (webhook sortant ou file d'attente) pousserait l'écriture vers
     le cœur métier de l'assureur, avec retry/statut de synchronisation.
  3. Authentification : la plupart des ERP d'assurance exposent du SOAP/XML
     propriétaire plutôt qu'une REST API moderne — prévoir une couche
     d'adaptation par ERP, pas un connecteur générique.
  Ceci reste une explication conceptuelle pour le pitch — ne pas coder de
  connecteur tant que ce n'est pas redemandé avec un ERP cible précis.
- Marketplace, multi-tenant, RBAC fin, scoring de fraude, autres branches
  (habitation/santé) — voir `CLAUDE.md` §3 pour la liste complète.

## 12. Historique des commits (dans l'ordre)

```
e3c0e0e Squelette : FastAPI+SQLite+seed calibré, front React/Vite/Tailwind 4 écrans
b253461 Backend complet : orchestrateur, 7 agents, HITL, audit, studio, dashboard
943f4b2 Frontend complet + script de démo : les 4 écrans branchés de bout en bout
e8b457f DA brand book + modele Haiku + croquis degats + reculer/rejouer + agent perso
cad0c3a Studio : rôle par défaut branchable + indice pipeline/hors-pipeline
b3b2c78 Studio ajoute (ne remplace plus), logo exact du brand book, ecran de connexion
1bd7a68 Capacite d'adaptation (piece manquante -> sans_suite), fix bug run stale, stub e-constat
```
Lire les messages de commit dans l'ordre donne l'historique complet des
décisions — ils sont volontairement détaillés (pas des "wip"/"fix").

## 13. Checklist avant de reprendre le travail

1. `git log --oneline` — confirmer que tu es bien sur `1bd7a68` ou plus
   récent, et `git status` propre (rien en attente non commité).
2. Lancer backend + frontend (§3), `curl -X POST http://localhost:8001/admin/reseed`.
3. `.venv/Scripts/python test_e2e.py` → doit afficher `TOUS LES TESTS PASSENT`.
   Si un test échoue, **c'est la priorité absolue** avant toute nouvelle
   fonctionnalité — ne jamais ajouter de code par-dessus une régression.
4. Si l'utilisateur demande une nouvelle fonctionnalité : relire `CLAUDE.md`
   §2-3 (scope gelé) avant d'écrire une ligne. En cas de doute sur le
   périmètre, proposer d'abord, coder ensuite.
5. Après toute modification backend touchant un router : redémarrer uvicorn
   (pas de `--reload` garanti actif selon comment il a été lancé — vérifier).
6. Après toute modification frontend : `npm run build` doit passer sans
   erreur avant de considérer le travail terminé.
7. Reseed avant de rendre la main à l'utilisateur pour une démo/répétition.
