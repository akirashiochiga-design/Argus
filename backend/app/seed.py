"""Données de référence nécessaires au fonctionnement d'Norix.

Usage :  python -m app.seed   (depuis backend/)
Réinitialise complètement norix.db — c'est le bouton "reset démo".
"""
from sqlmodel import SQLModel, Session

from .db import DB_PATH, create_db_and_tables, engine
from .models import Agent, MarketplaceListing, Police, Template, Workflow

# Barème de vétusté (valeurs plausibles — à confirmer avec l'encadrant Maghrebia)
BAREME_VETUSTE = [
    {"age_max": 2, "taux": 0.00},
    {"age_max": 5, "taux": 0.10},
    {"age_max": 8, "taux": 0.20},
    {"age_max": 99, "taux": 0.30},
]

def build_templates() -> list[Template]:
  return [
    Template(
        nom="Contrôle des pièces obligatoires",
        categorie="extraction",
        instructions_defaut=(
            "Vérifie que le dossier contient les justificatifs attendus selon le type "
            "de sinistre. Dresse la liste des pièces présentes, manquantes ou illisibles "
            "et prépare les éléments à demander au déclarant."
        ),
        garde_fous_defaut={
            "pas_de_decision_argent": True,
            "outils_autorises": ["inventorier_pieces", "consulter_circonstances"],
            "max_iterations_agent": 4,
        },
    ),
    Template(
        nom="Détection de dommages antérieurs",
        categorie="vision",
        instructions_defaut=(
            "Analyse les photos pour distinguer les dégâts récents des traces d'usure "
            "ou de réparations anciennes. Signale les indices observés et le niveau "
            "de confiance, sans se prononcer sur un montant."
        ),
        garde_fous_defaut={
            "pas_de_decision_argent": True,
            "outils_autorises": ["consulter_vehicule_assure", "inventorier_pieces"],
            "max_iterations_agent": 4,
        },
    ),
    Template(
        nom="Demande de complément à l'assuré",
        categorie="courrier",
        instructions_defaut=(
            "Rédige un message clair et courtois demandant uniquement les informations "
            "ou justificatifs manquants identifiés dans le dossier. Mentionne le numéro "
            "du dossier et les modalités de transmission."
        ),
        garde_fous_defaut={
            "pas_de_decision_argent": True,
            "pas_de_donnees_sensibles": True,
        },
    ),
]


def build_marketplace() -> list[MarketplaceListing]:
    """Templates vendus par des éditeurs tiers, installables en un clic."""
    commun = {"pas_de_decision_argent": True, "max_iterations_agent": 4}
    return [
        MarketplaceListing(
            nom="Lecture de constat auto",
            categorie="extraction",
            editeur="North Africa Claims Lab",
            description=(
                "Extrait les conducteurs, véhicules, circonstances et signatures "
                "depuis un constat amiable."
            ),
            prix=240,
            note=4.9,
            installations=128,
            tags=["Auto", "Documents"],
            verifie=True,
            statut="publie",
            instructions=(
                "Lis le constat amiable et extrais les conducteurs, véhicules, "
                "circonstances, cases cochées et signatures. Signale chaque champ "
                "illisible avec un niveau de confiance."
            ),
            garde_fous={**commun, "outils_autorises": ["inventorier_pieces"]},
        ),
        MarketplaceListing(
            nom="Évaluation dégâts carrosserie",
            categorie="vision",
            editeur="Vision Assur",
            description=(
                "Classe les dommages visibles et prépare une synthèse exploitable "
                "par le gestionnaire."
            ),
            prix=390,
            note=4.8,
            installations=94,
            tags=["Auto", "Vision"],
            verifie=True,
            statut="publie",
            instructions=(
                "Analyse les photos de carrosserie, localise les zones touchées et "
                "classe la gravité sans estimer ni recommander aucun montant."
            ),
            garde_fous={
                **commun,
                "outils_autorises": ["consulter_vehicule_assure", "inventorier_pieces"],
            },
        ),
        MarketplaceListing(
            nom="Assistant déclaration FNOL",
            categorie="fnol",
            editeur="Tunis Digital Insurance",
            description=(
                "Transforme une déclaration en français ou en darija en dossier "
                "sinistre structuré."
            ),
            prix=180,
            note=4.7,
            installations=211,
            tags=["Auto", "FNOL"],
            verifie=True,
            statut="publie",
            instructions=(
                "Structure la déclaration libre en faits, date, lieu, parties et "
                "pièces annoncées. N'invente jamais une information absente."
            ),
            garde_fous={**commun, "langues": ["fr", "darija"]},
        ),
        MarketplaceListing(
            nom="Contrôle de complétude",
            categorie="extraction",
            editeur="OpsFlow",
            description=(
                "Vérifie les pièces obligatoires et indique clairement les éléments "
                "encore manquants."
            ),
            prix=95,
            note=4.6,
            installations=76,
            tags=["Documents", "Contrôle"],
            verifie=False,
            statut="publie",
            instructions=(
                "Inventorie les pièces du dossier, contrôle leur lisibilité et produit "
                "la liste exacte des justificatifs manquants."
            ),
            garde_fous={**commun, "outils_autorises": ["inventorier_pieces"]},
        ),
        MarketplaceListing(
            nom="Rédaction décision assurée",
            categorie="courrier",
            editeur="ClearClaim",
            description=(
                "Rédige un courrier clair à partir des clauses et montants déjà "
                "validés par le gestionnaire."
            ),
            prix=150,
            note=4.8,
            installations=163,
            tags=["Courrier", "Conformité"],
            verifie=True,
            statut="publie",
            instructions=(
                "Rédige une décision compréhensible et cite les clauses fournies. "
                "Reprends uniquement le montant explicitement validé par le gestionnaire."
            ),
            garde_fous={**commun, "montant_impose": True},
        ),
    ]


def build_polices() -> list[Police]:
  return [
    Police(
        numero="PA-2024-1183",
        assure_nom="Ahmed Ben Salah",
        formule="tous_risques",
        garanties={
            "rc": {"plafond": None, "franchise": 0},
            "collision": {"plafond": 30000, "franchise": 220},
            "bris_glace": {"plafond": 1500, "franchise": 50},
            "vol_incendie": {"plafond": 45000, "franchise": 500},
        },
        prime_payee=True,
        vehicule={"marque": "Volkswagen", "modele": "Golf 8", "immatriculation": "225 TU 4817", "annee": 2022},
    ),
    Police(
        numero="PA-2023-0754",
        assure_nom="Fatma Trabelsi",
        formule="tiers",
        garanties={
            "rc": {"plafond": None, "franchise": 0},
            "bris_glace": {"plafond": 800, "franchise": 50},
        },
        prime_payee=True,
        vehicule={"marque": "Peugeot", "modele": "208", "immatriculation": "198 TU 2231", "annee": 2019},
    ),
    Police(
        numero="PA-2025-0212",
        assure_nom="Mohamed Gharbi",
        formule="tous_risques",
        garanties={
            "rc": {"plafond": None, "franchise": 0},
            "collision": {"plafond": 60000, "franchise": 400},
            "bris_glace": {"plafond": 2000, "franchise": 0},
            "vol_incendie": {"plafond": 90000, "franchise": 800},
        },
        prime_payee=True,
        vehicule={"marque": "Kia", "modele": "Sportage", "immatriculation": "247 TU 9902", "annee": 2025},
    ),
    Police(
        numero="PA-2022-1408",
        assure_nom="Leila Haddad",
        formule="tous_risques",
        garanties={
            "rc": {"plafond": None, "franchise": 0},
            "collision": {"plafond": 25000, "franchise": 300},
            "vol_incendie": {"plafond": 35000, "franchise": 500},
        },
        prime_payee=False,  # prime impayée → refus par le moteur de garanties
        vehicule={"marque": "Renault", "modele": "Clio 5", "immatriculation": "211 TU 5540", "annee": 2021},
    ),
    Police(
        numero="PA-2024-0967",
        assure_nom="Sami Bouazizi",
        formule="tiers",
        garanties={
            "rc": {"plafond": None, "franchise": 0},
        },
        prime_payee=True,
        vehicule={"marque": "Fiat", "modele": "Tipo", "immatriculation": "233 TU 1174", "annee": 2023},
    ),
    Police(
        numero="PA-2025-0533",
        assure_nom="Nour Chaabane",
        formule="tous_risques",
        garanties={
            "rc": {"plafond": None, "franchise": 0},
            "collision": {"plafond": 40000, "franchise": 200},
            "bris_glace": {"plafond": 1200, "franchise": 0},
        },
        prime_payee=True,
        vehicule={"marque": "Hyundai", "modele": "i20", "immatriculation": "251 TU 3308", "annee": 2025},
    ),
]


def build_agents(templates: list[Template]) -> list[Agent]:
    """Les 8 modules du traitement standard."""
    return [
        Agent(
            nom="Qualification initiale",
            categorie="fnol",
            instructions=(
                "À partir de la déclaration reçue en français ou en darija tunisienne, "
                "identifier le type de sinistre, la date, le lieu, les circonstances, "
                "les parties impliquées et les pièces annoncées. Signaler les champs "
                "manquants sans compléter une information absente."
            ),
            garde_fous={
                "pas_de_decision_argent": True,
                "langues": ["fr", "darija"],
                "outils_autorises": ["consulter_police", "inventorier_pieces"],
                "max_iterations_agent": 4,
            },
            statut="live",
        ),
        Agent(
            nom="Extraction documents",
            categorie="extraction",
            instructions=(
                "Lis le document (constat amiable ou facture de réparation) et "
                "extrais les champs typés : immatriculations, date, montants, postes "
                "de réparation. Donne une confiance par champ."
            ),
            garde_fous={"pas_de_decision_argent": True},
            statut="live",
        ),
        Agent(
            nom="Analyse des dégâts",
            categorie="vision",
            instructions=(
                "Analyse les photos de dégâts : classe leger/moyen/lourd, zones "
                "touchées et confiance. Ne réalise aucun contrôle de cohérence avec "
                "la déclaration : cette responsabilité appartient à un module séparé."
            ),
            garde_fous={
                "pas_de_decision_argent": True,
                "mission": "gravite",
                "outils_autorises": [
                    "consulter_vehicule_assure",
                    "consulter_circonstances",
                    "inventorier_pieces",
                ],
                "max_iterations_agent": 4,
            },
            statut="live",
        ),
        Agent(
            nom="Cohérence photo",
            categorie="vision",
            instructions=(
                "Compare les photos de dégâts avec les circonstances déclarées. "
                "Signale toute incohérence de zone, de type de dommage ou de véhicule, "
                "avec les éléments visuels observés et un niveau de confiance."
            ),
            garde_fous={
                "pas_de_decision_argent": True,
                "mission": "coherence",
                "outils_autorises": [
                    "consulter_vehicule_assure",
                    "consulter_circonstances",
                    "inventorier_pieces",
                ],
                "max_iterations_agent": 4,
            },
            statut="live",
        ),
        Agent(
            nom="Contrôle des garanties",
            categorie="garanties",
            instructions=(
                "Applique le contrat au sinistre : garantie couverte ou non, franchise "
                "et plafond applicables, motivation ligne à ligne avec clause citée."
            ),
            garde_fous={"deterministe": True},
            statut="live",
        ),
        Agent(
            nom="Évaluation indemnitaire",
            categorie="indemnite",
            instructions=(
                "Calcule le montant d'indemnité : base facture, vétusté selon le barème, "
                "franchise et plafond contractuel. Chaque ligne du calcul est sourcée."
            ),
            garde_fous={
                "deterministe": True,
                "hitl_obligatoire": True,
                "bareme_vetuste": BAREME_VETUSTE,
            },
            statut="live",
        ),
        Agent(
            nom="Validation gestionnaire",
            categorie="hitl",
            instructions=(
                "Route la recommandation : en dessous du seuil, tâche 'proposé' ; "
                "au-dessus, validation obligatoire."
            ),
            seuils={"plafond_auto": 500, "seuil_validation": 1000},
            garde_fous={"deterministe": True, "non_desactivable": True},
            statut="live",
        ),
        Agent(
            nom="Courrier de décision",
            categorie="courrier",
            instructions=(
                "Rédige la lettre de décision pour l'assuré : explication claire, "
                "clauses citées, dans la langue de l'assuré. Le montant est fourni "
                "par le calcul indemnitaire et validé par le gestionnaire."
            ),
            garde_fous={"montant_impose": True, "pas_de_donnees_sensibles": True},
            statut="live",
        ),
    ]


def seed() -> None:
    # Réinitialiser les tables plutôt que supprimer le fichier : sous Windows,
    # les requêtes de polling de l'interface peuvent conserver un handle ouvert.
    engine.dispose()
    SQLModel.metadata.drop_all(engine)
    create_db_and_tables()

    templates = build_templates()
    with Session(engine) as session:
        for t in templates:
            session.add(t)
        for p in build_polices():
            session.add(p)
        for listing in build_marketplace():
            session.add(listing)
        session.commit()

        agents = build_agents(templates)
        for a in agents:
            session.add(a)
        session.commit()

        # Le pipeline P5 enrichi : gravité et cohérence sont deux contrôles distincts
        workflow = Workflow(
            nom="Sinistre auto — de la déclaration au règlement",
            description="Traitement complet pour les collisions et dommages matériels.",
            est_defaut=True,
            etapes=[
                {"ordre": 0, "agent_id": agents[0].id, "type": "agent"},          # FNOL
                {"ordre": 1, "agent_id": agents[1].id, "type": "agent"},          # extraction
                {"ordre": 2, "agent_id": agents[2].id, "type": "agent"},          # gravité vision
                {"ordre": 3, "agent_id": agents[3].id, "type": "agent"},          # cohérence photo
                {"ordre": 4, "agent_id": agents[4].id, "type": "agent"},          # garanties (déterministe)
                {"ordre": 5, "agent_id": agents[5].id, "type": "agent"},          # indemnité (déterministe)
                {"ordre": 6, "agent_id": agents[6].id, "type": "porte_humaine"},  # HITL
                {"ordre": 7, "agent_id": agents[7].id, "type": "agent"},          # courrier
            ],
        )
        session.add(workflow)
        session.add(
            Workflow(
                nom="Bris de glace",
                description="Traitement allégé des déclarations liées au vitrage automobile.",
                est_defaut=False,
                etapes=[
                    {"ordre": 0, "agent_id": agents[0].id, "type": "agent"},
                    {"ordre": 1, "agent_id": agents[1].id, "type": "agent"},
                    {"ordre": 2, "agent_id": agents[4].id, "type": "agent"},
                    {"ordre": 3, "agent_id": agents[5].id, "type": "agent"},
                    {"ordre": 4, "agent_id": agents[6].id, "type": "porte_humaine"},
                    {"ordre": 5, "agent_id": agents[7].id, "type": "agent"},
                ],
            )
        )
        session.commit()

    print(f"Seed OK -> {DB_PATH}")
    print("  3 templates, 5 listings marketplace, 6 polices, 8 agents, 2 workflows, 0 dossier")


if __name__ == "__main__":
    seed()
