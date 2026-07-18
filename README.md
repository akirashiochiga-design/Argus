# Argus — l'ERP de l'IA agentique pour l'assurance

Argus permet aux compagnies d'assurance de **créer, connecter, gouverner et
superviser des agents d'IA** au sein de leurs opérations métier.

Créer un agent prend quelques heures. Le connecter au système d'information,
l'encadrer par les règles de l'assureur, le déployer et prouver chacune de ses
actions peut prendre plusieurs mois. **Le problème n'est pas l'IA : c'est son
passage en production.**

Argus apporte la couche opérationnelle entre les modèles d'IA, les systèmes de
l'assureur et les gestionnaires responsables des décisions.

## Vision produit

La plateforme est conçue autour de cinq capacités :

- **Créer** — studio sans code et modèles d'agents adaptés aux métiers de
  l'assurance.
- **Connecter et déployer** — intégration aux ERP, bases de données, outils
  documentaires et cores assurance sans remplacement du système existant.
- **Superviser** — contrôle humain, seuils, garde-fous et suivi des exécutions.
- **Mesurer** — coûts, délais, taux d'approbation, corrections et valeur créée.
- **Distribuer** — à terme, une marketplace d'agents métier pour les assureurs,
  éditeurs et intégrateurs.

Argus n'est pas limité à l'assurance automobile. Le produit cible l'ensemble des
branches et processus assurantiels : sinistres, souscription, conformité,
service client et opérations internes.

## Ce que démontre ce dépôt

Ce dépôt implémente un premier parcours complet sur un **sinistre automobile
matériel**. L'automobile est le cas d'usage de référence utilisé pour prouver
l'architecture ; ce n'est pas le périmètre final du produit.

Le parcours opérationnel comprend :

1. structuration d'une déclaration en français ou en darija tunisienne ;
2. lecture d'un constat, d'une facture ou d'un devis ;
3. analyse visuelle des dégâts et détection d'incohérences ;
4. application des garanties, franchises et plafonds contractuels ;
5. calcul du montant indemnitaire selon les règles de gestion ;
6. suspension obligatoire avant toute décision financière ;
7. approbation, modification ou refus par un gestionnaire ;
8. rédaction du courrier de décision ;
9. journal d'audit horodaté et supervision des indicateurs.

Le dossier de référence **SIN-2026-001** aboutit à une proposition de
**1 850 DT** : facture de 2 300 DT, moins la vétusté et la franchise.

## Principes de gouvernance

Argus sépare explicitement les responsabilités :

> **L'IA lit, extrait et explique. Les règles calculent. L'humain décide. Tout
> est tracé.**

- Aucun modèle ne décide seul d'un montant ou d'un paiement.
- Toute décision financière exige une action humaine explicite.
- Chaque exécution, modification et décision produit un événement d'audit.
- Les règles contractuelles et les barèmes restent exécutés par du code
  contrôlable.
- Les agents personnalisés ne peuvent pas contourner les contrôles financiers.

## Différenciation

- **Contexte assurantiel local** — darija tunisienne, constat amiable, contrats
  et barèmes du marché.
- **Intégration au système existant** — l'assureur conserve son core, ses données
  et ses processus.
- **Gouvernance intégrée** — contrôle humain, audit et explicabilité ne sont pas
  ajoutés après coup.
- **Déploiement maîtrisable** — architecture conçue pour pouvoir être hébergée
  au plus près du système et des exigences de résidence des données.
- **Studio métier** — création d'agents spécialisés sans confier les décisions
  engageant l'assureur à un modèle.

## Fonctionnalités disponibles

- Studio de création, publication et configuration d'agents
- Parcours visuel d'un dossier et exécution étape par étape
- Extraction de documents et analyse d'images avec l'API Anthropic
- Moteur de garanties et calcul indemnitaire par règles métier
- File d'approbation humaine
- Courrier de décision
- Dashboard de supervision et journal d'audit
- Interface de configuration des ERP et bases de données
- Déploiement frontend et backend sous une URL unique

Les connecteurs ERP réels, la marketplace, le multi-tenant et le déploiement
chez l'assureur font partie des prochaines étapes. L'écran d'intégrations de
ce prototype présente le parcours de configuration, sans connexion à un ERP
de production.

## Architecture

- **Frontend** — React, Vite et Tailwind CSS
- **Backend** — Python et FastAPI
- **Données** — SQLite pour le prototype
- **IA** — API Anthropic, texte et vision
- **Orchestration** — machine à états explicite
- **Déploiement** — image Docker unique, compatible Railway

## Lancer en local

### 1. Backend

```sh
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m app.seed
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

Le backend est disponible sur `http://localhost:8000`.

### 2. Frontend

```sh
cd frontend
npm install
npm run dev
```

Le frontend est disponible sur `http://localhost:5173`.

### 3. Configuration de l'IA

Créer un fichier `.env` non versionné :

```env
ANTHROPIC_API_KEY=your_anthropic_api_key
ARGUS_MODEL=claude-haiku-4-5
```

Le modèle peut être remplacé par une autre référence Anthropic compatible via
`ARGUS_MODEL`.

## Déployer

Le `Dockerfile` à la racine compile le frontend puis le sert avec FastAPI. Sur
Railway :

1. créer un projet depuis ce dépôt GitHub ;
2. ajouter `ANTHROPIC_API_KEY` dans les variables du service ;
3. générer un domaine dans **Settings → Networking**.

Railway détecte automatiquement `railway.json` et publie toute la plateforme
sous une URL unique.

## Documentation

- [Cahier des charges](docs/cahier-des-charges.pdf)
- [Brand book](docs/Argus-Brand-Book.html)
- [Script de présentation technique](docs/script-video-2-minutes.html)
- [Guide de démonstration](docs/demo.md)

## Équipe

- **Zakaria** — finance et investissement
- **Khalil** — stratégie et entrepreneuriat IA
- **Rayen** — ingénierie et intelligence artificielle

Argus part de la Tunisie comme terrain de preuve, avec l'ambition de devenir la
couche de déploiement et de gouvernance des agents d'IA pour l'assurance en
Afrique du Nord, dans la zone CIMA et dans le Golfe.
