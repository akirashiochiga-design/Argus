# Script de démo — Argus (5-6 minutes)

> Objectif : le jury doit repartir avec 3 idées. **(1)** On crée un agent d'assurance
> sans code en 30 secondes. **(2)** Jamais d'IA sur une décision d'argent : calcul
> déterministe + humain obligatoire. **(3)** Tout est audité — c'est déployable chez
> un assureur réel demain matin.

---

## AVANT la démo (checklist J-1 et H-1)

**J-1 :**
- [ ] **Photos de dégâts** : des **croquis d'expertise** sont générés
      automatiquement (`degats-1/2/3.jpg`, `parebrise.jpg` — vue de dessus, zone
      endommagée hachurée). Ça suffit pour la démo. Les remplacer par de vraies
      photos si vous en trouvez (regénérer les croquis : `python -m app.samples`).
- [ ] Clé API configurée dans `backend/.env` : `GEMINI_API_KEY=...` et
      `GEMINI_MODEL=gemini-3.1-flash-lite` (vision comprise, quota gratuit
      ~1000 req/j sur ce modèle — `gemini-2.5-flash` et `gemini-3.5-flash` sont
      HS sur ce compte au 2026-07-20, cf. HANDOFF.md). `ANTHROPIC_API_KEY` reste
      configurée en secours (`LLM_PROVIDER=anthropic` si Gemini retombe en
      quota pendant la démo — nécessite du crédit sur le compte Anthropic).
      Tous les agents LLM appellent le fournisseur configuré en direct —
      badges **IA** dans l'UI.
- [ ] Répétition générale : `POST /admin/reseed` (via le bouton **↻ Reset démo**
      ou `curl`) puis dérouler un dossier dans l'UI jusqu'au bout. **Ne pas se
      fier à `test_e2e.py`** — il teste un ancien jeu de dossiers fictifs
      (`SIN-2026-00x`) retiré du seed le 2026-07-19 et n'a pas été remis à jour
      (voir HANDOFF.md §2).
- [ ] Faire relire les déclarations darija du seed par un locuteur (fichier `backend/app/seed.py`).

**H-1 (sur la machine de démo) :**
- [ ] Terminal 1 : `cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8001`
- [ ] Terminal 2 : `cd frontend && npm run dev`
- [ ] Ouvrir http://localhost:5173 — vérifier le badge vert « connecté ».
- [ ] **Reset démo** : `curl -X POST http://localhost:8001/admin/reseed`
      (à refaire entre chaque répétition — reconstruit templates/agents/polices
      ET reconnecte+resynchronise CoreSinistre, ce qui fait apparaître les
      dossiers `EXT-SIN-2026-1002`/`1003`).
- [ ] Zoom navigateur 110-125 % pour le projecteur.

**Contrôles de démo (dans l'app) :**
- **↻ Reset démo** (en haut à droite) : reconstruit l'état de référence ET les
  dossiers CoreSinistre entre deux passages, sans toucher au terminal.
- **◀ Reculer** (Pipeline) : annule la dernière étape — pratique si vous cliquez
  trop vite ou voulez remontrer un agent.
- **↺ Rejouer** (Pipeline) : remet le dossier courant au début pour le rejouer en direct.

**Plan B intégré (à connaître, pas à dire) :** si le Wi-Fi tombe ou l'API LLM
est indisponible (quota/crédit épuisé), les agents LLM basculent automatiquement
sur leurs fallbacks déterministes/heuristiques (même résultat final, calcul et
gouvernance identiques) — mais le contrôle de cohérence photo perd alors sa
valeur (il ne compare plus vraiment texte et image, il retombe sur une réponse
par défaut). Si ça arrive en répétition, relancer le serveur backend après
avoir vérifié `GEMINI_MODEL`/`ANTHROPIC_API_KEY` dans `.env`. Si on vous
demande en direct : « c'est un garde-fou de production — un assureur ne peut
pas arrêter de traiter des sinistres à cause d'une API indisponible. »

---

## LE DÉROULÉ

### 0. Accroche (30 s) — écran Pipeline affiché
> « Un sinistre auto en Tunisie, c'est en moyenne des semaines de traitement.
> Argus le fait en 2 minutes, sans jamais laisser une IA décider d'un dinar.
> On vous montre un vrai dossier, de la déclaration au règlement. »

### 1. La déclaration (45 s) — Pipeline
- Après un **↻ Reset démo**, deux dossiers apparaissent via la synchro
  CoreSinistre. Montrer **EXT-SIN-2026-1003** : pare-brise fissuré par un
  gravier sur autoroute (Volkswagen Golf 8, tous risques).
- Montrer la frise : 7 agents, dont la **porte humaine** (bouclier) au milieu.
  > « Chaque boîte est un agent. Les violets appellent le LLM, les verts sont du
  > code pur. La règle : le LLM lit et explique, il ne calcule jamais l'argent. »

### 2. L'exécution (60 s) — le moment signature
- Cliquer **▶ Exécuter le pipeline**. Commenter au fil de l'animation :
  - FNOL : « déclaration structurée, bris de glace, complétude 88 % »
  - Extraction : « il lit le devis du garage : 420 DT »
  - Gravité : « photo analysée : impact central, fissures rayonnantes, cohérent »
  - Garanties : « tous risques, bris de glace couvert, clause citée (Art. 5) »
  - Indemnité : « 420 − 80 DT de franchise = **340 DT**.
    Ce calcul est du code, pas un LLM — il est rejouable et opposable. »
- Le pipeline **s'arrête tout seul** sur la porte humaine :
  > « Même à 340 dinars, sous le seuil, Argus ne règle rien sans un humain — ce
  > n'est pas une option, c'est non désactivable. »
- (Dossier de secours : **EXT-SIN-2026-1002**, formule **tiers** — la garantie
  collision n'y est pas souscrite → refus motivé clause par clause, Art. 4. Bon
  filet si le premier dossier a un problème réseau en plein exposé.)

### 3. La décision humaine (45 s) — Approbations
- Cliquer « Ouvrir la file d'approbation ». Dérouler la synthèse :
  > « Le gestionnaire a tout : la couverture motivée clause par clause, le calcul
  > ligne à ligne. Il peut approuver, corriger le montant, ou refuser. »
- Cliquer **✓ Approuver 340 DT** → message vert → « Voir le dossier » :
  la lettre à l'assuré est générée, clauses citées, dossier **réglé**.

### 4. Le studio — créer un agent en live (75 s) — le moment waouh
> « Tout ce que vous venez de voir a été assemblé sans code. La preuve, en direct. »
- **Créer un agent personnalisé** (encadré terracotta en haut) : taper une phrase,
  ex. *« un agent qui vérifie la cohérence entre les photos et la déclaration »*,
  puis **✦ Générer les instructions**.
  > « Je décris ce que je veux, l'IA rédige la consigne de l'agent. » (Badge **IA**
  > = génération Claude en direct.)
- Choisir le rôle « Analyse d'images », **Créer l'agent** → il apparaît avec le
  badge **✦ perso**. Montrer l'encadré 🔒 :
  > « Même en écrivant ce que je veux, impossible de créer un agent qui décide d'un
  > montant ou saute la validation humaine. La gouvernance n'est pas contournable. »
- (Optionnel) template « Recommandation de règlement » → **Créer**, **Publier**,
  **Brancher au pipeline** → le pipeline live se met à jour.
- Sur « Porte de validation humaine » → **Seuils** → 1000 → 300 → Enregistrer :
  > « Je viens de durcir la gouvernance de toute la compagnie en un clic — versionné, audité. »

### 5. La preuve par l'audit (45 s) — Dashboard & Audit
- Montrer les tuiles : coût IA (« quelques cents par dossier »), temps économisé,
  taux de correction (« l'écart humain/agent : c'est notre métrique de confiance »).
- Filtrer le journal sur « humains » :
  > « Voici ce qu'un auditeur ou un régulateur verrait : qui a décidé quoi, quand,
  > sur quelle proposition. Append-only. C'est la condition pour mettre de l'IA
  > dans l'assurance — et c'est le cœur d'Argus, pas une feature. »

### 6. Fermeture (20 s)
> « Aujourd'hui : la branche auto, 7 agents, un pilote possible immédiatement.
> Demain : habitation, santé, la marketplace d'agents certifiés entre assureurs.
> Argus, c'est l'usine à agents d'assurance — gouvernée by design. »

### Si le jury veut un rappel (2 min bonus)
- Déclarer un sinistre en live : Pipeline → « + Déclarer un sinistre » →
  « Remplir l'exemple » (pare-brise 380 DT, police de Mohamed) → Créer → Exécuter.
  Avec le seuil abaissé à 300, ce petit dossier exige maintenant une validation :
  la gouvernance changée au §4 s'applique en direct.
- Dossier **EXT-SIN-2026-1002** : refus motivé clause par clause (formule tiers,
  garantie collision absente), confirmé par l'humain, courrier de refus.

---

## Questions probables du jury

| Question | Réponse |
|---|---|
| « L'IA peut se tromper sur un montant ? » | Non : le montant est calculé par du code (barème + franchise), le LLM ne fait que lire les documents. Et un humain valide tout règlement. |
| « Et si l'API Claude tombe pendant la prod ? » | Fallback dégradé automatique + file d'attente ; le calcul et la gouvernance sont locaux. Démontrable ici même en coupant le Wi-Fi. |
| « Ça coûte combien ? » | ~2-4 cents d'IA par dossier (affiché au dashboard) contre ~2 h de gestionnaire. |
| « RGPD / données sensibles ? » | Piste d'audit native, données locales dans ce POC ; roadmap : résidence des données, masquage des PII dans les prompts, modèle souverain. |
| « Pourquoi pas un simple workflow BPM ? » | Le BPM ne lit ni une déclaration en darija, ni une facture photographiée, ni des photos de dégâts. Argus combine ça avec la rigueur du BPM. |

## Reset entre deux passages
```sh
curl -X POST http://localhost:8001/admin/reseed
```
