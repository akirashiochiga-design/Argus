# Cahier des charges Argus — référence condensée

> Version texte condensée pour lecture par Claude Code. Le PDF complet
> (`cahier-des-charges.pdf`) fait foi ; ce fichier extrait ce qui sert au code
> du hackathon : vocabulaire, principes de gouvernance, parcours P5, entités.

## Vision (M1.2)
Plateforme no-code pour créer, connecter, exploiter et acheter des agents d'IA
d'assurance, point d'entrée sur la gestion des sinistres (déclaration→paiement).
Passer de plusieurs mois à quelques jours, sans projet d'intégration lourd.
Trois difficultés absorbées : construction (no-code métier), connexion (ERP/MCP),
distribution (marketplace).

## Les 8 modules (vision complète — voir CLAUDE.md pour ce qu'on code)
- M2 Studio d'agents (construction no-code)
- M3 Déploiement et connexion (ERP, système cœur, MCP)
- M4 Marketplace (publication/acquisition)
- M5 Console opérations et monitoring
- M6 Analytics, reporting, gestion des modèles/LLM
- M7 Gouvernance, sécurité, conformité, permissions
- M8 Parcours, modèle de données, non-fonctionnel, roadmap

## Principes directeurs NON NÉGOCIABLES (M1.6)
- **Human-in-the-loop sur l'argent** : toute décision engageant un versement,
  un montant, un rejet financier ou un ordre de paiement est validée par un
  humain avant exécution. Non désactivable pour la catégorie paiement.
- **Auditabilité par défaut** : chaque run/tâche/décision tracé, horodaté,
  attribué à une identité (humaine ou agent), rattaché à la version exacte.
  Piste d'audit consultable, exportable, inaltérable (append-only).
- **Configurabilité sans code** : profils métier configurent agents/règles/seuils.
- **Séparation des tâches** : construire ≠ déployer ≠ approuver ≠ contrôler.
- **Sécurité des secrets** : coffre, jamais en clair, usage journalisé.
- **Résidence/souveraineté** : choix du lieu de traitement, option modèle local.
- **Multilinguisme** : arabe (dont darija) + français.
- **Réversibilité** : tout versionné, tout déploiement réversible.
- **Garde-fous explicites** : périmètre d'outils, plafonds, obligations HITL.
- **Mesurabilité** : coût, débit, délai de cycle, taux STP, taux de correction.

## Les templates d'agents assurance (M2.1.2)
1. **FNOL bilingue** — conduit la déclaration (darija/FR), collecte et structure.
   Entrées : messages déclarant, n° police, canal. Sorties : dossier FNOL
   structuré (type, date, lieu, circonstances, parties, pièces), champs
   manquants, score de complétude, langue.
2. **Extraction documentaire (OCR)** — constat, facture, ordonnance, PV.
   Sorties : champs typés + confiance par champ + qualité image.
3. **Tri de gravité par vision** — photos → classe (léger/moyen/lourd/épave),
   zones de dommage, confiance, incohérence image/déclaration.
4. **Scoring de fraude** — score + signaux + recommandation. [HORS SCOPE hackathon]
5. **Moteur de garanties et règles** — couverture par garantie, franchise,
   plafond, exclusions, motivation ligne à ligne, clause citée. → DÉTERMINISTE.
6. **Recommandation de règlement** — montant + détail du calcul (barème,
   vétusté, franchise), fourchette, seuil de validation humaine. → DÉTERMINISTE.
7. **Orchestration de paiement** — prépare l'ordre après validation. Validation
   humaine avant tout mouvement de fonds NON DÉSACTIVABLE.
8. **Communication client** — accusé, demande de pièces, notification décision.
   Relecture humaine activable par type de message.
Adjacents : KYC, routage courrier, complétude docs, doublons, synthèse dossier.

## Parcours P5 — Traiter un sinistre auto avec HITL (LE parcours de démo)
1. Assuré déclare via canal connecté → agent FNOL collecte, joint pièces
   (constat, photos, facture), identifie police, crée Dossier état "reçu".
2. Agent extraction/OCR lit les documents, structure les champs.
3. Agent tri de gravité (vision) analyse photos → niveau + confiance.
4. [Agent fraude — hors scope hackathon] score + signaux.
5. Moteur de garanties → position de couverture motivée (franchises, plafonds).
6. Agent recommandation de règlement → montant + décision + justification.
7. **HITL obligatoire** : tâche au gestionnaire. Console présente dossier
   synthétisé (faits, garanties, gravité, recommandation, montant, sources) →
   approuver / modifier / refuser / demander pièce / escalader.
8. Gestionnaire vérifie, ajuste, motive, approuve. Écart proposition/décision
   enregistré (taux de correction).
9. Si montant > seuil → second HITL (superviseur).
10. Agent orchestration paiement prépare le règlement. Aucune sortie d'argent
    sans confirmation humaine explicite. Auteur/horodatage/montant journalisés.
11. Écriture propagée au système cœur via connecteur ERP [simulé en hackathon].
12. Agent communication informe l'assuré, dans sa langue, sans données sensibles.
13. Dossier → "réglé" → "clôturé". Tout consigné dans la piste d'audit.

## Entités du modèle de données (M8.3) — noms à réutiliser
Organisation, Utilisateur, Rôle/Permission, Équipe, Modèle-template, Agent,
Version, Workflow, Connecteur, Secret, Déploiement, Dossier/Sinistre, Tâche,
Run/Exécution, Événement d'audit, Listing marketplace, Abonnement, Budget,
Métrique, Notification/Alerte.

(Pour le hackathon on ne garde que : Template, Agent, Workflow, Dossier, Run,
Tâche, ÉvénementAudit — voir CLAUDE.md section 6.)

### Dossier/Sinistre (M8.3.12) — champs clés
référence, branche(auto/habitation/santé), police+assuré, état(reçu|en_cours|
en_attente_humaine|en_exception|réglé|refusé|clôturé), gravité estimée, score
fraude, position de couverture, montant_recommandé, montant_validé, pièces,
canal d'origine.

### Run/Exécution (M8.3.14) — champs clés
agent/workflow+version, environnement, début/fin, statut(succès|échec|interrompu
|en_attente_humaine), étapes et appels d'outils, entrées/sorties, jetons, coût,
latence, indice de confiance, décisions produites.

### Tâche (M8.3.13) — champs clés
type(validation HITL|demande pièce|exception|escalade|confirmation paiement),
état, priorité, âge, délai cible, contexte présenté, décision + motif. Une tâche
de décision d'argent exige un rôle habilité.

### Événement d'audit (M8.3.15) — champs clés
type, acteur(humain|agent), horodatage, objet, avant/après, motif, résultat.
Immuable. Couvre toute décision d'argent, communication sortante, promotion prod,
lecture de secret, changement de rôle.

## Gestion du risque modèle (M7.5) — utile pour le pitch gouvernance
- Garde-fous entrée/sortie, anti-injection (contenu tiers = donnée, pas commande).
- Score de confiance → sous un plancher, l'agent s'abstient et route vers humain.
- Détection sorties non ancrées (hallucination) : montants rattachés à une source.
- Explicabilité : facteurs, règles appliquées, pièces utilisées, versions.

## Roadmap (M8.5) — pour la slide "et après"
- **MVP** : chaîne FNOL→règlement sur branche auto, 1 assureur pilote Tunisie.
  (= ce qu'on démontre au hackathon)
- **v1** : plus de branches (habitation, santé), workflows conditionnels, vision
  + fraude, connecteurs élargis, budgets/alertes, marketplace côté acheteur.
- **v2** : marketplace biphase (éditeurs tiers, certification, revenus, fork),
  déploiements souverains (modèle local), multi-régions CIMA + Golfe.
