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
- Extraction de documents et analyse d'images avec Gemini, avec secours Anthropic
- Moteur de garanties et calcul indemnitaire par règles métier
- File d'approbation humaine
- Courrier de décision
- Dashboard de supervision et journal d'audit
- Registre d'adaptateurs : core assurance, documents SharePoint et écritures ERP
- Marketplace persistante : soumission de templates et installation immédiate dans le Studio
- Portail freelance séparé (`/#editeur`) pour publier et suivre ses templates
- Déploiement frontend et backend sous une URL unique

Le paiement et le reversement Marketplace, la certification complète, les
identifiants OAuth/ERP de production, le multi-tenant et le Relay déployé chez
l'assureur font partie des prochaines étapes. Le prototype connecte réellement
une base assurance externe locale ; les adaptateurs SharePoint et ERP interne utilisent
des sources locales clairement signalées comme simulations de démonstration.

## Architecture

- **Frontend** — React, Vite et Tailwind CSS
- **Backend** — Python et FastAPI
- **Données** — SQLite pour le prototype
- **IA** — API Gemini, texte, vision et outils métier
- **Orchestration** — machine à états explicite
- **Déploiement** — image Docker unique, compatible Railway

## Lancer en local

### 1. Backend

```sh
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m app.seed
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8001
```

Le backend est disponible sur `http://localhost:8001`.

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
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```

La clé gratuite se crée dans [Google AI Studio](https://aistudio.google.com/app/apikey).
Une configuration Anthropic existante reste utilisable en secours.

## Déployer

Le `Dockerfile` à la racine compile le frontend puis le sert avec FastAPI. Sur
Railway :

1. créer un projet depuis ce dépôt GitHub ;
2. ajouter `GEMINI_API_KEY` dans les variables du service ;
3. générer un domaine dans **Settings → Networking**.

Railway détecte automatiquement `railway.json` et publie toute la plateforme
sous une URL unique.

## Documentation

- [Cahier des charges](docs/cahier-des-charges.pdf)
- [Brand book](docs/Argus-Brand-Book.html)
- [Script de présentation technique](docs/script-video-2-minutes.html)
- [Guide de démonstration](docs/demo.md)
- [Speech démo, marché et business model](docs/pitch-speech-6-7-demo.md)

## Équipe

- **Zakaria** — finance et investissement
- **Khalil** — stratégie et entrepreneuriat IA
- **Rayen** — ingénierie et intelligence artificielle

Argus part de la Tunisie comme terrain de preuve, avec l'ambition de devenir la
couche de déploiement et de gouvernance des agents d'IA pour l'assurance en
Afrique du Nord, dans la zone CIMA et dans le Golfe.
