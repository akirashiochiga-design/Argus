# CLAUDE.md — Argus (Hackathon build)

> Ce fichier est la source de vérité pour toute session de travail sur ce dépôt.
> Lis-le en entier avant d'écrire du code. En cas de doute, le périmètre gelé
> (section "SCOPE — CE QU'ON CONSTRUIT") prime sur tout le reste.

## 1. Contexte

Argus est une plateforme SaaS B2B qui permet à une compagnie d'assurance de
**créer, déployer, exploiter et auditer des agents d'IA** pour la gestion des
sinistres — sans écrire de code, avec l'humain qui valide toute décision qui
engage de l'argent, et une piste d'audit complète.

Ce dépôt est développé pendant un **hackathon de 3 jours (vendredi→dimanche),
équipe de 3 personnes**. Le juge doit voir tourner en direct la chaîne complète
d'un sinistre auto, de la déclaration au règlement, plus la création d'un agent
en live dans le studio.

La spécification produit complète (8 modules, ~30 agents, marketplace, RBAC fin,
multi-tenant, connecteurs ERP réels…) est dans `docs/cahier-des-charges.md`.
**C'est la VISION, PAS le périmètre de code du hackathon.** Ne l'implémente pas
en entier. Elle sert de référence sémantique : noms d'entités, vocabulaire
métier, règles de gouvernance. Le périmètre réel à coder est ci-dessous.

## 2. SCOPE — CE QU'ON CONSTRUIT (gelé)

La boucle démontrable, sur **une seule branche : auto / collision matérielle** :

**CRÉER** — un studio minimal (formulaire, pas de builder graphique) pour
instancier un agent depuis un template : nom, rôle, template métier, seuils,
règle d'approbation. 3 templates suffisent au départ : FNOL, moteur de garanties,
recommandation de règlement.

**GOUVERNER** — human-in-the-loop : toute décision d'argent passe par une file
d'approbation où un humain approuve / modifie / refuse. Guardrails visibles
(plafond auto, seuil de validation). Piste d'audit horodatée de chaque action.

**EXÉCUTER** — un moteur d'orchestration qui fait passer un dossier sinistre à
travers un pipeline d'agents. Déclenchement MANUEL (bouton "Exécuter"), jamais
de scheduler en démo.

**AUDITER** — dashboard de supervision (dossiers par état, coût, temps
économisé, taux d'approbation) + journal d'audit consultable.

### Les agents réellement implémentés (le pipeline P5 du cahier des charges)
1. **FNOL** — lit une déclaration (texte libre FR/darija) → dossier structuré
2. **Extraction docs** — lit un constat / une facture (image ou PDF) → champs (LLM multimodal, 1 appel API)
3. **Gravité vision** — analyse photo(s) de dégâts → classe léger/moyen/lourd (LLM multimodal)
4. **Moteur de garanties** — applique le contrat (garantie couverte ? franchise ? plafond ?) → position de couverture. CODE DÉTERMINISTE, PAS DE LLM.
5. **Calcul indemnité** — montant après franchise/vétusté. CODE DÉTERMINISTE, PAS DE LLM.
6. **Human-in-the-loop** — routage : sous seuil = proposé, au-dessus = validation obligatoire.
7. **Rédaction courrier** — lettre de décision expliquée, clauses citées (LLM).

## 3. HORS SCOPE (ne PAS construire — c'est de la roadmap pour le pitch)

Ne code aucun de ces éléments, même s'ils sont détaillés dans le cahier des
charges. S'ils apparaissent, ce sont des libellés "à venir" dans l'UI, jamais du
code fonctionnel :

- Marketplace (M4) entière : publication, certification, achat, fork, revenus.
- Multi-tenant réel / isolation inter-organisations. Un seul tenant en dur.
- RBAC fin. Un login factice + un rôle "superviseur" suffisent.
- Vrais connecteurs ERP / core insurance / MCP. Tout est simulé par des données locales.
- Coffre à secrets, rotation de clés, environnements bac-à-sable vs prod séparés.
- Versioning / rollback des agents, promotion, déploiement en un clic.
- Scoring de fraude, graphe de fraude, doublons, subrogation, provisions, reporting réglementaire.
- Modèle local/souverain, routage/repli LLM, budgets, alertes de coût.
- Multi-branches (habitation, santé, vie…). AUTO uniquement.
- Envoi de vrais emails/SMS. Utiliser Mailtrap/Mailhog ou une simulation.
- Webhooks, API publique, exposition MCP inverse.

Si une tâche demandée sort de ce périmètre, signale-le et propose la version
"stub / simulée" au lieu de la construire pour de vrai.

## 4. Stack (à confirmer à l'init, mais préférence)

- Frontend : React + Vite + Tailwind. 4 écrans : Studio, Pipeline (vue dossier qui avance), File d'approbation, Dashboard + Journal d'audit.
- Backend : Python + FastAPI.
- Données : SQLite (via SQLModel/SQLAlchemy) — PAS de PostgreSQL, pas de Docker obligatoire pour la démo. Un fichier SQLite suffit et se réinitialise facilement.
- LLM : API Anthropic (Claude). Clé lue depuis une variable d'environnement `ANTHROPIC_API_KEY`, jamais en dur.
- Emails : simulation (log + affichage UI) ou Mailhog si le temps le permet.
- Orchestration : machine à états maison simple (dict d'étapes + statut). PAS de LangGraph/CrewAI sauf accord explicite — on veut du code lisible et débogable à 3h du matin.

## 5. Principes de gouvernance NON NÉGOCIABLES (dans le code)

Ces règles viennent des principes directeurs du cahier des charges (M1.6) et
doivent être vraies dans le code, car c'est le cœur du pitch :

- **Jamais de LLM sur une décision d'argent.** Le montant est calculé par du code déterministe (règles + barème). Le LLM prépare, explique, extrait — il ne décide pas du montant.
- **Human-in-the-loop obligatoire sur l'argent.** Aucun paiement/règlement n'est marqué "envoyé" sans une action humaine explicite. Non désactivable.
- **Tout est tracé.** Chaque exécution d'agent, chaque décision humaine, chaque changement d'état écrit un événement d'audit horodaté (qui/quoi/quand/version).
- **Les données sensibles ne partent pas en clair** dans les prompts au-delà du nécessaire (au minimum, en avoir conscience et masquer ce qui peut l'être).

## 6. Modèle de données (minimal, inspiré de M8.3)

Garde les noms d'entités du cahier des charges pour cohérence, mais réduits :

- `Agent` : id, nom, catégorie, template_origine, instructions, seuils (json), garde-fous (json), version, statut(draft|live)
- `Workflow` : id, nom, étapes (liste ordonnée d'agent_id + type de nœud), statut
- `Dossier` (sinistre) : id, ref, branche(auto), assuré, police, état(reçu|en_cours|attente_validation|réglé|refusé|clôturé), gravité, position_couverture(json), montant_recommandé, montant_validé, pièces(json)
- `Run` : id, dossier_id, agent_id, entrées(json), sorties(json), coût, durée, statut, confiance
- `Tache` (HITL) : id, dossier_id, type, état, montant, proposition(json), décision, motif, validateur
- `EvenementAudit` : id, acteur(humain|agent), type, objet, avant(json), après(json), motif, horodatage
- `Template` : id, nom, catégorie, instructions_défaut, garde-fous_défaut

## 7. Dataset de démo (à générer, calibré)

Un script `seed.py` crée des données fictives réalistes pour la démo :
- 5-6 assurés avec noms tunisiens, polices auto, garanties variées (tiers, tous risques), primes payées/impayées.
- Barème de vétusté et grille de franchise (à confirmer avec l'encadrant Maghrebia — valeurs plausibles en attendant).
- 2-3 dossiers sinistres prêts, dont un calibré pour la démo live : un choc matériel qui aboutit à ~1 850 DT après franchise (le chiffre du pitch).
- Fichiers d'exemple : une image de constat/facture et 2-3 photos de dégâts auto (à placer dans `docs/samples/`, testées avec le prompt vision AVANT la démo).

## 8. Ordre de construction (respecter cette séquence)

1. Squelette : repo, FastAPI qui démarre, React qui démarre, SQLite + modèles, `seed.py`. (Vendredi soir)
2. Le pipeline auto fonctionnel côté backend : les 7 agents, orchestrateur, sur un dossier du seed. Calcul déterministe du montant. (Samedi matin)
3. File d'approbation + audit : l'humain valide, tout est tracé. (Samedi aprem)
4. Studio (créer un agent depuis template) + vue pipeline animée dans l'UI. (Samedi soir)
5. Dashboard + polish. Deuxième template créable en live pour l'effet "waouh". (Dimanche matin)

Chaque étape doit laisser l'app dans un état DÉMONTRABLE. On préfère 3 agents qui
tournent de bout en bout à 7 agents à moitié câblés.

## 9. Conventions

- Réponses et commentaires de code peuvent être en français (équipe FR).
- Commits petits et fréquents.
- Avant d'ajouter une dépendance lourde, demande.
- Ne jamais committer de clé API. `.env` dans `.gitignore`.
- Quand tu proposes une archi ou un gros changement, montre-le et attends validation avant de coder.
