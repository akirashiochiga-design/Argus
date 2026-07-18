# Script de démo — Argus (5-6 minutes)

> Objectif : le jury doit repartir avec 3 idées. **(1)** On crée un agent d'assurance
> sans code en 30 secondes. **(2)** Jamais d'IA sur une décision d'argent : calcul
> déterministe + humain obligatoire. **(3)** Tout est audité — c'est déployable chez
> un assureur réel demain matin.

---

## AVANT la démo (checklist J-1 et H-1)

**J-1 :**
- [ ] Déposer de **vraies photos de dégâts auto** dans `docs/samples/` :
      `degats-1.jpg`, `degats-2.jpg` (avant droit endommagé), `degats-3.jpg` (capot),
      `parebrise.jpg` (fissure). Les documents (facture, devis, constat) sont déjà
      générés — les remplacer par de vrais scans si possible.
- [ ] Mettre la clé dans `backend/.env` : `ANTHROPIC_API_KEY=sk-ant-...`
      → les agents FNOL/extraction/gravité/courrier passent en vrais appels Claude
      (badge violet **LLM** dans l'UI au lieu de **simulé**).
- [ ] Répétition générale : `cd backend && .venv/Scripts/python test_e2e.py`
      → doit afficher `TOUS LES TESTS PASSENT`.
- [ ] Faire relire les déclarations darija du seed par un locuteur (fichier `backend/app/seed.py`).

**H-1 (sur la machine de démo) :**
- [ ] Terminal 1 : `cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000`
- [ ] Terminal 2 : `cd frontend && npm run dev`
- [ ] Ouvrir http://localhost:5173 — vérifier le badge vert « connecté ».
- [ ] **Reset démo** : `curl -X POST http://localhost:8000/admin/reseed`
      (à refaire entre chaque répétition — remet les 3 dossiers à zéro).
- [ ] Zoom navigateur 110-125 % pour le projecteur.

**Plan B intégré (à connaître, pas à dire) :** si le Wi-Fi tombe ou la clé API expire,
les agents LLM basculent automatiquement en mode simulation (badge gris « simulé »),
le calcul et la gouvernance restant identiques. La démo ne peut pas planter.
Si on vous le demande : « le fallback est un garde-fou de production, pas un artifice
de démo — un assureur ne peut pas arrêter de traiter des sinistres parce qu'une API
est indisponible. »

---

## LE DÉROULÉ

### 0. Accroche (30 s) — écran Pipeline affiché
> « Un sinistre auto en Tunisie, c'est en moyenne des semaines de traitement.
> Argus le fait en 2 minutes, sans jamais laisser une IA décider d'un dinar.
> On vous montre un vrai dossier, de la déclaration au règlement. »

### 1. La déclaration (45 s) — Pipeline
- Montrer le dossier **SIN-2026-001** : lire 2 lignes de la déclaration d'Ahmed
  (texte libre). Mentionner : « ça marche aussi en darija — dossier 2 ».
- Montrer la frise : 7 agents, dont la **porte humaine** (bouclier) au milieu.
  > « Chaque boîte est un agent. Les violets appellent Claude, les verts sont du
  > code pur. La règle : le LLM lit et explique, il ne calcule jamais l'argent. »

### 2. L'exécution (60 s) — le moment signature
- Cliquer **▶ Exécuter le pipeline**. Commenter au fil de l'animation :
  - FNOL : « déclaration structurée, langue détectée, complétude »
  - Extraction : « il lit la facture du garage : 2 300 DT »
  - Gravité : « photos analysées : dégâts moyens, cohérents avec la déclaration »
  - Garanties : « tous risques, collision couverte, chaque clause citée »
  - Indemnité : « 2 300 − 10 % de vétusté − 220 de franchise = **1 850 DT**.
    Ce calcul est du code, pas un LLM — il est rejouable et opposable. »
- Le pipeline **s'arrête tout seul** sur la bannière ambre :
  > « Et là, tout s'arrête. 1 850 dinars vont sortir : Argus refuse de continuer
  > sans un humain. Ce n'est pas une option, c'est non désactivable. »

### 3. La décision humaine (45 s) — Approbations
- Cliquer « Ouvrir la file d'approbation ». Dérouler la synthèse :
  > « Le gestionnaire a tout : la couverture motivée clause par clause, le calcul
  > ligne à ligne. Il peut approuver, corriger le montant, ou refuser. »
- Cliquer **✓ Approuver 1 850 DT** → message vert → « Voir le dossier » :
  la lettre à l'assuré est générée, clauses citées, dossier **réglé**.

### 4. Le studio — créer un agent en live (60 s)
> « Tout ce que vous venez de voir a été assemblé sans code. La preuve. »
- Studio → template « Recommandation de règlement » → **Créer un agent** :
  nom « Règlement auto — bris de glace », seuil 300 DT → Créer.
- Montrer les 🔒 : « les garde-fous du template sont hérités, non désactivables —
  un métier ne peut pas se créer un agent qui contourne la gouvernance. »
- **Publier**, puis **Brancher au pipeline** → montrer le pipeline live mis à jour.
- Sur « Porte de validation humaine » → **Seuils** → passer 1000 → 300 → Enregistrer :
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
- Dossier SIN-2026-002 (darija) : refus motivé clause par clause, confirmé par
  l'humain, courrier de refus avec délai de recours.

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
curl -X POST http://localhost:8000/admin/reseed
```
