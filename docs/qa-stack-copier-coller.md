# Q&A — comprendre et expliquer la stack Argus

## Réponse courte à dire au jury

« Notre frontend est construit avec React, Vite et Tailwind CSS. Le backend est une API Python avec FastAPI. Les données applicatives sont stockées dans SQLite à travers SQLModel, qui repose sur SQLAlchemy. Pour l'intelligence artificielle multimodale, nous utilisons Gemini 2.5 Flash par défaut, avec Claude comme fournisseur alternatif. L'orchestration est une machine à états développée en Python, sans framework agentique lourd. Enfin, Docker assemble le frontend et le backend dans une seule image, puis Railway déploie l'ensemble derrière une URL unique. »

## Frontend

### React

React sert à construire l'interface utilisateur sous forme de composants réutilisables.

Dans Argus, il gère notamment :

- la liste et le détail des dossiers ;
- l'animation du pipeline ;
- le Studio de création d'agents ;
- la file d'approbation humaine ;
- le dashboard et le journal d'audit ;
- l'état de l'interface pendant les appels au backend.

Phrase simple :

« React construit les écrans et met l'interface à jour lorsque les données d'un dossier changent. »

### Vite

Vite est l'outil de développement et de compilation du frontend.

Il sert à :

- lancer rapidement le frontend en local ;
- recharger l'interface pendant le développement ;
- transformer le code React en fichiers optimisés pour la production.

Vite n'est pas le serveur métier et ne traite aucun dossier.

Phrase simple :

« Vite nous permet de développer rapidement puis de compiler React en fichiers statiques optimisés. »

### Tailwind CSS

Tailwind CSS sert à construire le design directement avec des classes utilitaires.

Dans Argus, il gère :

- les couleurs et la typographie ;
- les espacements et les grilles ;
- les états visuels du pipeline ;
- les badges, boutons, cartes et vues responsives.

Phrase simple :

« Tailwind CSS gère toute la présentation visuelle sans ajouter un gros framework de composants. »

## Backend

### Python

Python contient toute la logique métier d'Argus :

- orchestration du pipeline ;
- moteur de garanties ;
- calcul déterministe de l'indemnité ;
- création des tâches de validation ;
- appels aux modèles d'IA ;
- écriture de la piste d'audit.

Phrase simple :

« Python porte la logique métier, notamment les règles financières qui doivent rester déterministes et auditables. »

### FastAPI

FastAPI expose les fonctionnalités Python sous forme d'API HTTP.

Le frontend l'appelle pour :

- lire ou créer un dossier ;
- lancer une étape du pipeline ;
- approuver, modifier ou refuser une proposition ;
- créer des agents et des workflows ;
- consulter les indicateurs et l'audit ;
- synchroniser la base assurance.

FastAPI fournit aussi la validation des données entrantes et la documentation automatique de l'API.

Phrase simple :

« FastAPI est la porte d'entrée du backend : React lui envoie des requêtes et il exécute la logique métier correspondante. »

### Uvicorn

Uvicorn est le serveur qui fait réellement tourner l'application FastAPI.

Phrase simple :

« FastAPI définit l'API ; Uvicorn est le serveur qui l'écoute et répond aux requêtes. »

## Données

### SQLite

SQLite est la base de données utilisée par le prototype. Elle stocke les agents, workflows, dossiers, exécutions, tâches humaines et événements d'audit dans un fichier local.

Pourquoi ce choix :

- aucune infrastructure de base de données à administrer pendant le hackathon ;
- démarrage et réinitialisation rapides ;
- suffisant pour une démonstration avec peu d'utilisateurs concurrents.

Limite assumée :

Pour une production multi-utilisateurs ou multi-tenant, la cible serait PostgreSQL.

Phrase simple :

« SQLite nous donne une vraie base relationnelle sans serveur supplémentaire ; PostgreSQL sera utilisé lorsque la concurrence et le multi-tenant le nécessiteront. »

### SQLModel

SQLModel relie les classes Python aux tables de la base.

Il sert à :

- définir les modèles de données ;
- lire et écrire les enregistrements ;
- contrôler les types ;
- réduire le SQL écrit à la main.

### SQLAlchemy

SQLAlchemy est le moteur ORM utilisé sous SQLModel. Il gère les connexions, les sessions et la traduction des opérations Python en requêtes SQL.

Phrase simple :

« SQLModel nous donne des modèles Python simples, et SQLAlchemy exécute les opérations SQL derrière. »

### Base assurance externe

Argus possède aussi un connecteur en lecture seule vers une base SQLite qui simule le core insurance d'un assureur.

Le connecteur :

- vérifie le schéma de la source ;
- importe les polices, garanties, véhicules et sinistres ;
- évite les doublons grâce aux références ;
- laisse la base source inchangée.

Phrase simple :

« La base Argus stocke le traitement, tandis qu'un connecteur en lecture seule synchronise les données venant du système d'assurance. »

## Intelligence artificielle

### Gemini 2.5 Flash

Gemini 2.5 Flash est le modèle utilisé par défaut lorsqu'une clé `GEMINI_API_KEY` est disponible.

Il sert aux tâches non déterministes :

- comprendre une déclaration en français ou en darija ;
- extraire les informations d'un document ;
- analyser des photos de dégâts ;
- rédiger un courrier expliqué.

Il ne calcule jamais l'indemnité et ne valide jamais un paiement.

### Claude / API Anthropic

Claude est pris en charge comme fournisseur alternatif lorsqu'une clé Anthropic est configurée.

Cette abstraction évite de rendre l'application dépendante d'un seul fournisseur.

Phrase simple :

« Le modèle lit et explique les données non structurées, mais les décisions financières restent dans du code Python déterministe et passent toujours par un humain. »

### Pillow

Pillow est une bibliothèque Python de traitement d'images.

Elle prépare les images avant leur envoi au modèle multimodal, par exemple pour les ouvrir, vérifier leur format ou les redimensionner.

### Variables d'environnement

Les clés d'API et le choix du modèle sont fournis par des variables d'environnement telles que `GEMINI_API_KEY` et `ANTHROPIC_API_KEY`.

Elles ne sont pas écrites dans le code ni versionnées dans Git.

Phrase simple :

« Les secrets sont injectés au déploiement par des variables d'environnement, jamais codés en dur. »

## Orchestration

### Machine à états maison

Argus n'utilise pas LangChain, LangGraph ou CrewAI.

Un workflow est une liste ordonnée d'étapes. Chaque appel exécute une seule étape, enregistre son résultat et fait avancer le dossier.

Ce choix apporte :

- un comportement facile à lire et à déboguer ;
- des étapes testables séparément ;
- un contrôle strict sur les transitions ;
- une piste d'audit claire ;
- aucune abstraction cachée autour des décisions financières.

Phrase simple :

« Notre orchestrateur est une machine à états Python volontairement simple : une étape entre, produit une sortie auditée, puis le dossier change d'état. »

### Human-in-the-loop

La validation humaine est une étape obligatoire du workflow.

Quand le pipeline l'atteint :

- une tâche d'approbation est créée ;
- le dossier passe en attente ;
- aucun règlement ne peut être marqué comme validé ;
- seul un humain peut approuver, modifier ou refuser.

Phrase simple :

« L'humain n'est pas une option ajoutée à l'interface : c'est une porte bloquante dans le moteur d'orchestration. »

### Audit append-only

Chaque action importante crée un événement horodaté avec l'acteur, l'objet, l'état avant, l'état après et le motif.

L'API ne propose aucune route de modification ou de suppression de ces événements.

Phrase simple :

« Chaque action laisse une trace immuable exploitable par un superviseur ou un auditeur. »

## Déploiement

### Docker

Docker construit une image reproductible en deux étapes :

1. Node compile le frontend React avec Vite.
2. Python installe le backend, récupère le frontend compilé et lance FastAPI avec Uvicorn.

En production, FastAPI sert donc à la fois l'API et les fichiers du frontend.

Phrase simple :

« Docker assemble toute la plateforme dans un seul paquet reproductible, identique en local et dans le cloud. »

### Railway

Railway construit l'image Docker, lance le service et vérifie son état grâce à la route `/health`.

Phrase simple :

« Railway héberge l'image Docker et expose toute la plateforme derrière une URL unique. »

### Node.js et npm

Node.js est utilisé uniquement pour installer et compiler les dépendances du frontend. `npm` garantit une installation reproductible à partir du fichier de verrouillage.

Node.js ne porte pas la logique métier en production.

## Flux complet d'une requête

1. L'utilisateur clique sur « Lancer le traitement » dans React.
2. React appelle une route FastAPI.
3. FastAPI charge le dossier avec SQLModel depuis SQLite.
4. L'orchestrateur détermine l'étape courante.
5. Si nécessaire, l'étape appelle Gemini ou Claude pour lire du contenu non structuré.
6. Les garanties et le montant sont calculés par du code Python déterministe.
7. Le résultat et l'événement d'audit sont enregistrés dans SQLite.
8. FastAPI renvoie le nouvel état à React.
9. React met à jour la frise du pipeline.
10. À la porte humaine, le traitement s'arrête jusqu'à la décision d'un gestionnaire.

## Questions pièges et réponses

**Pourquoi avoir deux fournisseurs d'IA ?**

« Pour éviter le verrouillage fournisseur et disposer d'un repli. Le reste de l'architecture ne dépend pas du modèle choisi. »

**Est-ce que changer de modèle peut modifier les montants ?**

« Non. Le modèle ne calcule aucun montant. Les règles de couverture, la franchise et la vétusté sont exécutées par du code Python déterministe. »

**Pourquoi ne pas tout faire avec l'IA ?**

« Parce qu'une décision financière doit être reproductible, testable et explicable. L'IA traite le contenu non structuré ; le moteur de règles décide selon le contrat. »

**SQLite est-il prêt pour une grande compagnie ?**

« Non, et ce n'est pas ce que nous prétendons. Il convient au prototype et au pilote mono-tenant. SQLModel nous permet ensuite de migrer vers PostgreSQL sans réécrire la logique métier. »

**Le frontend peut-il contourner la validation ?**

« Non. Le blocage est appliqué dans le backend et dans l'état du dossier, pas seulement dans l'interface. Une requête directe ne peut donc pas contourner la porte humaine. »

**Que se passe-t-il si le LLM est indisponible ?**

« Le pipeline conserve sa structure et ses garde-fous. Les étapes disposent de sorties de repli pour la démonstration, et aucune indisponibilité du modèle ne peut autoriser automatiquement une décision financière. »
