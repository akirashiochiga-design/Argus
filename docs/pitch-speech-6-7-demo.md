# Ton passage — démo + slides 6 & 7 (cible 75–90s)

Basé sur `Argus-Pitch (2).pdf` (11 slides) et l'état réel de la plateforme
(`docs/demo.md`, code backend/frontend). Enchaînement : ton collègue termine la
slide 5 (« Cinq briques ») → toi : démo live (~30s) → slide 6 (marché) → slide 7
(business model).

**Préparation IMPORTANTE (à faire avant de monter) :**
- Fais un reset, puis exécute et approuve **SIN-2026-001** avant de monter :
  la démo montre un résultat déjà complet, sans attendre un appel LLM.
- Ouvre d'abord **Supervision & Audit**. Tu parcourras ensuite la barre de
  navigation strictement de droite à gauche : **Intégrations → Marketplace →
  Studio → Approbations → Sinistres**.
- Dans **Sinistres**, garde **SIN-2026-001** sélectionné et descends jusqu'à
  **Historique du traitement**. C'est l'image finale de la démo.
- Ne clique sur aucune action pendant ces 30 secondes : tu montres la boucle,
  tu ne la rejoues pas.

---

## 0. Transition (2-3s, pendant que tu changes d'écran)

> « Plutôt que de vous l'expliquer, je vous montre. »

## 1. Démo live — ~30 secondes

**[Supervision & Audit — montrer les KPI et le journal]**

> « En trente secondes, voici toute la boucle Argus. Ici, l'assureur supervise
> ses dossiers, ses coûts et chaque décision. »

**[Clic vers la gauche : Intégrations]**

> « Argus se branche à son système existant, sans le remplacer. »

**[Clic vers la gauche : Marketplace]**

> « Dans la Marketplace, l'assureur peut acheter des agents spécialisés ou
> publier les siens. »

**[Clic vers la gauche : Studio]**

> « Dans le Studio, le métier crée ses agents, avec des garde-fous verrouillés. »

**[Clic vers la gauche : Approbations]**

> « Dès qu'un montant est engagé, l'IA s'arrête : un gestionnaire approuve,
> modifie ou refuse. »

**[Clic vers la gauche : Sinistres — SIN-2026-001 — descendre à l'historique]**

> « Et sur chaque dossier, on retrouve le parcours complet : huit étapes,
> 1 850 dinars validés, et un historique d'exécution horodaté, donc totalement
> auditable. »

*(~97 mots : environ 32-36s. Enchaîne les clics pendant les phrases et termine
immobile sur l'historique du traitement.)*

---

## 2. Slide 6 — Le marché (~25s)

> « Pourquoi commencer par les sinistres ? Parce que c'est là que l'assureur
> dépense le plus : environ 70% de ses coûts. En Tunisie, il y a 22 assureurs :
> le marché est assez concentré pour qu'on puisse signer vite. Ensuite, on peut
> répliquer la même plateforme dans les 14 pays de la zone CIMA, puis dans le
> Golfe, où les primes représentent 48 milliards de dollars. »

*(~65 mots ≈ 23-26s)*

## 3. Slide 7 — Business model (~25s)

> « On facture 13 000 dinars par mois, plus 50 000 dinars pour l'intégration au
> départ. Prenons un assureur qui gère 100 000 sinistres par an : ses frais de
> gestion tournent autour de 17 millions de dinars. S'il en automatise seulement
> un quart, il économise environ 4,25 millions. La première année, Argus lui
> coûte 206 000 dinars. Même avec des hypothèses prudentes, le retour est très
> clair. »

*(~70 mots ≈ 25-28s)*

---

## Total & conseils de débit

- Démo (~35s) + slide 6 (~24s) + slide 7 (~26s) ≈ **85s**, dans la cible
  75-90s.
- Si tu es speed sur scène (l'adrénaline accélère toujours le débit), tu es en
  sécurité. Si tu sens que tu vas déborder : coupe la dernière phrase de
  chaque bloc (« Vingt fois le retour » et « c'est ce verrou-là qui manque à
  tout le monde » sont les deux premières à sacrifier — elles closent bien
  mais ne portent pas d'info nouvelle).
- Ralentis sur la dernière formule — « horodaté, donc totalement auditable » —
  et laisse l'historique affiché pendant la transition vers la slide 6.
- Ne lis jamais les chiffres sur la slide en même temps que tu les dis : dis-les
  en regardant la salle, la slide est là pour ceux qui veulent vérifier après.
- La comparaison à Lovable a déjà été faite en slide 4 par un autre — ne la
  répète pas dans ta transition, ça sonnerait comme une redite. Rebondis
  plutôt sur ce que ton collègue vient tout juste de dire (les cinq briques,
  « le verrou », etc.) pour que l'enchaînement paraisse continu, pas comme
  deux discours collés.

---

# Q&A technique — anticiper les questions du jury

## Stack & architecture

**Quelle est votre stack ?**
Frontend React + Vite + Tailwind. Backend Python + FastAPI. Base de données
SQLite via SQLModel (SQLAlchemy) — un seul fichier, zéro dépendance externe
à faire tourner. Un seul Dockerfile qui build le frontend et le sert depuis
FastAPI : toute la plateforme derrière une URL unique, déployée sur Railway.

**Pourquoi SQLite et pas Postgres ?**
Choix de hackathon délibéré, pas une limite d'architecture : SQLModel est
l'ORM, la bascule vers Postgres est un changement de connection string, pas
une réécriture. Pour un pilote à un assureur, un seul tenant, SQLite fait le
travail et se réinitialise en une commande. On passe à Postgres au premier
vrai client multi-utilisateurs concurrents.

**Quel modèle d'IA utilisez-vous ?**
Gemini 2.5 Flash par défaut (quota gratuit, multimodal — texte, image,
appel d'outils). Le code supporte aussi Claude (Haiku/Sonnet/Opus) en
bascule, on l'a gardé actif comme filet de secours. Le choix du fournisseur
est une variable d'environnement, pas un choix figé dans le code — on n'est
pas mariés à un seul labo.

**Pourquoi pas LangChain / LangGraph / CrewAI ?**
Décision d'équipe consciente : une machine à états maison, un dict d'étapes
et de statuts. À 3h du matin en hackathon, on voulait du code qu'on peut
déboguer en le lisant, pas une abstraction de framework à comprendre en
plus du bug. Chaque étape est une fonction Python testable isolément. Pour
la version produit, on regardera ce qui apporte vraiment de la valeur
(reprise sur erreur, observabilité), mais on ne réintroduira pas de la
complexité gratuite.

**Comment fonctionne l'orchestration concrètement ?**
Un `Workflow` est une liste ordonnée d'étapes, chaque étape pointe vers un
`Agent`. Un appel à `avancer()` exécute UNE étape et s'arrête — c'est le
frontend qui enchaîne les appels, ce qui donne l'animation qu'on voit à
l'écran. La porte humaine est une étape comme les autres dans cette liste :
quand on l'atteint, le dossier passe en `attente_validation` et rien ne peut
le faire avancer sauf une décision humaine explicite.

**Comment un agent "personnalisé" créé depuis un prompt dans le Studio est-il
sécurisé ?**
Il ne peut être créé que dans un rôle prédéfini (lecture de déclaration,
extraction de document, analyse d'image, rédaction de courrier). Il n'existe
tout simplement pas de catégorie d'agent "calcule un montant" ou "valide un
paiement" accessible depuis le créateur de prompt — ce n'est pas une
règle qu'on vérifie après coup, c'est une catégorie qui n'existe pas dans le
code. Un agent généré par prompt peut au mieux s'insérer comme étape
supplémentaire dans le pipeline, jamais remplacer le moteur de garanties, le
calcul d'indemnité ou la porte humaine.

## Gouvernance & fiabilité de l'IA

**L'IA peut-elle se tromper sur un montant ?**
Non, structurellement : le montant de l'indemnité sort d'une fonction Python
pure (barème de vétusté + grille de franchise), zéro appel LLM dans ce
chemin de code. Le LLM lit la déclaration, la facture, les photos — il
prépare et explique, il ne calcule jamais l'argent. Et même ce calcul
déterministe ne part jamais tout seul : il passe systématiquement par la
validation humaine avant de devenir un "montant validé".

**Et si l'API du LLM tombe pendant une démo ou en production ?**
Chaque agent a un fallback déterministe ou heuristique codé en dur. Si la clé
API est absente ou que l'appel échoue, l'agent bascule automatiquement dessus
— même structure de sortie, même gouvernance, le pipeline ne plante jamais.
On peut couper le wifi en plein direct, la démo continue.

**Comment vous assurez-vous que rien ne contourne la validation humaine ?**
C'est un champ de la base : `montant_valide` n'est écrit que par la fonction
de décision humaine (`decider()`), jamais par un agent. L'état "réglé" n'est
atteignable que si une tâche a été explicitement décidée par un humain — c'est
un invariant du moteur d'orchestration, documenté en commentaire dans le code
et vérifié par nos tests de bout en bout.

**Le journal d'audit, ça ressemble à quoi techniquement ?**
Une table `EvenementAudit`, append-only par design : aucun endpoint UPDATE ou
DELETE n'existe sur cette table dans l'API. Chaque exécution d'agent, chaque
décision humaine, chaque changement d'état, chaque modification de seuil ou
d'instructions d'agent y écrit une ligne horodatée avec l'acteur, l'objet, un
avant/après en JSON et un motif. C'est ce qu'un auditeur ou un régulateur
consulterait.

**Comment gérez-vous les langues (darija, français) ?**
Le modèle multimodal lit directement le texte libre, français ou darija
tunisienne, sans étape de traduction intermédiaire qui perdrait de
l'information. On a fait relire les déclarations du jeu de données par un
locuteur natif pour valider la justesse du parsing.

## Données & sécurité

**Où sont stockées les données sensibles ?**
Tout est local dans ce prototype — pas d'envoi à un tiers hors l'appel API au
LLM lui-même, avec seulement les champs nécessaires au traitement de l'étape.
Sur la roadmap produit : masquage systématique des données personnelles avant
envoi au prompt, résidence des données chez l'assureur ou dans sa zone, et
option de modèle local/souverain pour les clients qui l'exigent.

**RGPD, conformité ?**
La piste d'audit native est déjà la moitié du travail de conformité. Ce qui
manque aujourd'hui, volontairement laissé hors du périmètre hackathon : RBAC
fin, isolation multi-tenant réelle, coffre à secrets et rotation de clés. Ce
sont des chantiers connus, pas des angles morts qu'on découvrirait en
prod.

**C'est multi-tenant ?**
Pas encore : un tenant en dur pour la démo, un rôle superviseur unique.
L'architecture (agents, workflows, dossiers scopés par organisation) est
pensée pour, mais l'isolation stricte inter-organisations est un chantier
volontairement mis après le premier pilote signé — pas avant.

## Produit & roadmap

**Pourquoi pas un simple workflow BPM classique ?**
Un BPM ne lit pas une déclaration écrite en darija, ne lit pas une facture
photographiée au téléphone, ne regarde pas une photo de dégâts pour juger la
gravité. Argus combine cette lecture non structurée avec la rigueur d'un
moteur de règles — le BPM sait faire la deuxième moitié, pas la première.

**Ça coûte combien par dossier ?**
Quelques centimes de dollar d'appel IA par dossier (affiché en direct au
dashboard), contre en moyenne plusieurs heures de gestionnaire pour le même
traitement. C'est visible ligne par ligne, dossier par dossier — pas une
estimation.

**Combien de temps pour brancher un agent chez un vrai assureur ?**
Aujourd'hui, dans le pitch : un après-midi pour créer l'agent, contre 6 à 18
mois pour le brancher au core et le mettre en prod dans l'existant. C'est
exactement le problème qu'Argus résout — la couche de déploiement et de
gouvernance entre le modèle et le système d'information, pas juste un
créateur d'agents de plus.

**Vous ciblez que l'assurance auto ?**
Pour la preuve de concept, oui — une seule branche, sinistre matériel auto,
volontairement pour aller au bout d'un parcours démontrable plutôt que de
saupoudrer sur plusieurs branches à moitié câblées. L'architecture (agents,
workflow, garde-fous) n'a rien de spécifique à l'auto ; habitation et santé
sont la suite naturelle, pas une refonte.

**Et la marketplace, elle existe vraiment ?**
L'expérience est démontrable dans ce build : on peut parcourir et filtrer les
agents, simuler un achat ou une installation, et soumettre un agent à la
publication. Les transactions, la certification et la distribution entre
organisations sont volontairement simulées ; le cœur réellement connecté au
backend reste la boucle créer → gouverner → exécuter → auditer.

## Équipe & exécution

**Vous êtes combien, et qui fait quoi ?**
Trois. Zakaria vient de la finance et du private equity, Khalil de la
stratégie et de l'entrepreneuriat en IA agentique, Rayen de l'ingénierie et
de l'IA. On couvre la chaîne : lever, vendre, et construire.

**Pourquoi vous, pourquoi maintenant ?**
Parce qu'on n'a pas commencé par une démo Lovable pour un blog produit — on a
appelé des assureurs tunisiens, audité leurs systèmes gratuitement, et compris
que le problème n'est jamais "créer un agent", c'est "le faire vivre dans un
système réglementé, avec un humain qui reste responsable de chaque dinar".
