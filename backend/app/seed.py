"""Dataset de démo calibré (CLAUDE.md section 7).

Usage :  python -m app.seed   (depuis backend/)
Réinitialise complètement argus.db — c'est le bouton "reset démo".

Calibrage du dossier vedette SIN-2026-001 :
  facture 2 300 DT − vétusté 10 % (véhicule 2022, barème 3-5 ans) = 2 070
  − franchise collision 220 DT = 1 850 DT  ← le chiffre du pitch.
"""
from sqlmodel import Session

from .db import DB_PATH, create_db_and_tables, engine
from .models import Agent, Dossier, Police, Template, Workflow

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
        nom="Agent FNOL bilingue",
        categorie="fnol",
        instructions_defaut=(
            "Tu reçois une déclaration de sinistre auto en texte libre, en français "
            "ou en darija tunisienne. Structure-la : type de sinistre, date, lieu, "
            "circonstances, parties impliquées, pièces annoncées. Liste les champs "
            "manquants et donne un score de complétude. Ne jamais inventer une "
            "information absente du texte."
        ),
        garde_fous_defaut={"pas_de_decision_argent": True, "langues": ["fr", "darija"]},
    ),
    Template(
        nom="Moteur de garanties",
        categorie="garanties",
        instructions_defaut=(
            "Applique le contrat au sinistre : garantie couverte ou non, franchise "
            "et plafond applicables, motivation ligne à ligne avec clause citée."
        ),
        garde_fous_defaut={"deterministe": True},
    ),
    Template(
        nom="Recommandation de règlement",
        categorie="indemnite",
        instructions_defaut=(
            "Calcule le montant d'indemnité : base facture − vétusté (barème) − "
            "franchise, plafonné. Chaque ligne du calcul est sourcée. "
            "La validation humaine est obligatoire au-dessus du seuil."
        ),
        garde_fous_defaut={"deterministe": True, "hitl_obligatoire": True},
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
    """Les 7 agents du pipeline P5, instanciés depuis les templates quand il y en a un."""
    return [
        Agent(
            nom="FNOL auto",
            categorie="fnol",
            template_id=1,
            instructions=templates[0].instructions_defaut,
            garde_fous=templates[0].garde_fous_defaut,
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
            nom="Gravité vision",
            categorie="vision",
            instructions=(
                "Analyse les photos de dégâts : classe leger/moyen/lourd, zones "
                "touchées, cohérence avec les circonstances déclarées, confiance."
            ),
            garde_fous={"pas_de_decision_argent": True},
            statut="live",
        ),
        Agent(
            nom="Moteur de garanties auto",
            categorie="garanties",
            template_id=2,
            instructions=templates[1].instructions_defaut,
            garde_fous=templates[1].garde_fous_defaut,
            statut="live",
        ),
        Agent(
            nom="Calcul indemnité auto",
            categorie="indemnite",
            template_id=3,
            instructions=templates[2].instructions_defaut,
            garde_fous={**templates[2].garde_fous_defaut, "bareme_vetuste": BAREME_VETUSTE},
            statut="live",
        ),
        Agent(
            nom="Porte de validation humaine",
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
            nom="Rédaction courrier décision",
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


DECLARATION_1 = (
    "Bonjour, hier soir vers 19h30 je rentrais du travail sur l'avenue Habib "
    "Bourguiba à l'Ariana. Une voiture qui sortait d'un parking m'a percuté à "
    "l'avant droit. Le pare-chocs et le phare sont cassés, l'aile est enfoncée. "
    "On a rempli un constat amiable sur place, l'autre conducteur a reconnu son "
    "tort. J'ai des photos des dégâts et la facture du garage. Ma police est la "
    "PA-2024-1183. Ahmed Ben Salah."
)

DECLARATION_2 = (
    "Aslema, ena Fatma Trabelsi, police PA-2023-0754. El bare7 fi soir kont "
    "rekiya fi parking devant el dar, sob7 l9it el karhba mkhabta mel guedem, "
    "el capot ou el pare-chocs mkassrin. Ma3rafnech chkoun 3malha, ma famech "
    "constat. 3andi taswir. Chnoua na3mel ?"
)

DECLARATION_3 = (
    "Bonjour, ce matin sur la route de La Marsa un camion a projeté un gravier "
    "qui a fissuré mon pare-brise côté conducteur. La fissure fait environ 30 cm. "
    "Je vous joins la photo et le devis du poseur. Police PA-2025-0533, "
    "Nour Chaabane."
)

DECLARATION_4 = (
    "Bonjour, mon véhicule a été accroché hier après-midi sur le parking du "
    "supermarché — le pare-chocs arrière est rayé et légèrement enfoncé. Je "
    "n'ai pas encore de devis du garage, je vous l'enverrai dès que je "
    "l'aurai. Police PA-2025-0212. Mohamed Gharbi."
)


def build_dossiers() -> list[Dossier]:
    return [
        # LE dossier de la démo live : tous risques, collision → ~1 850 DT
        # + une photo de pare-brise (incohérente) pour démontrer la création d'agent
        Dossier(
            ref="SIN-2026-001",
            police_id=1,
            workflow_id=1,
            declaration_texte=DECLARATION_1,
            pieces=[
                {"type": "constat", "chemin": "docs/samples/constat.jpg", "montant": None},
                {"type": "facture", "chemin": "docs/samples/facture.jpg", "montant": 2300.0},
                {
                    "type": "photo_degats",
                    "chemin": "docs/samples/degats-1.jpg",
                    "montant": None,
                    "coherence_attendue": True,
                },
                {
                    "type": "photo_degats",
                    "chemin": "docs/samples/degats-2.jpg",
                    "montant": None,
                    "coherence_attendue": True,
                },
                {
                    "type": "photo_degats",
                    "chemin": "docs/samples/parebrise.jpg",
                    "montant": None,
                    # Vérité terrain du dataset, utilisée uniquement par le fallback
                    # de démo si l'API vision est indisponible.
                    "incoherente_declaration": True,
                    "coherence_attendue": False,
                    "motif_incoherence": (
                        "La photo montre un pare-brise fissuré, sans rapport avec le choc "
                        "avant droit déclaré (pare-chocs, phare et aile)."
                    ),
                },
            ],
        ),
        # Formule tiers, dégâts collision sans tiers identifié → non couvert → refus motivé
        Dossier(
            ref="SIN-2026-002",
            police_id=2,
            workflow_id=1,
            declaration_texte=DECLARATION_2,
            pieces=[
                {
                    "type": "photo_degats",
                    "chemin": "docs/samples/degats-3.jpg",
                    "montant": None,
                    "coherence_attendue": True,
                },
                {"type": "devis", "chemin": "docs/samples/devis.jpg", "montant": 1750.0},
            ],
        ),
        # Bris de glace, petit montant → sous le seuil, règlement "proposé"
        Dossier(
            ref="SIN-2026-003",
            police_id=6,
            workflow_id=1,
            declaration_texte=DECLARATION_3,
            pieces=[
                {
                    "type": "photo_degats",
                    "chemin": "docs/samples/parebrise.jpg",
                    "montant": None,
                    "coherence_attendue": True,
                },
                {"type": "devis", "chemin": "docs/samples/devis-parebrise.jpg", "montant": 420.0},
            ],
        ),
        # Capacité d'adaptation : couvert, mais AUCUNE pièce chiffrée jointe
        # (l'assuré n'a pas encore de devis) → l'agent 5 ne devine pas un
        # montant, il route vers "demande_piece". Laissé à l'état "reçu" :
        # à exécuter en direct pendant la démo pour montrer cette porte.
        Dossier(
            ref="SIN-2026-004",
            police_id=3,
            workflow_id=1,
            declaration_texte=DECLARATION_4,
            pieces=[
                {
                    "type": "photo_degats",
                    "chemin": "docs/samples/degats-3.jpg",
                    "montant": None,
                    "incoherente_declaration": True,
                    "coherence_attendue": False,
                    "motif_incoherence": (
                        "La photo montre des dégâts majeurs à l'avant du véhicule, alors que "
                        "la déclaration mentionne seulement un pare-chocs arrière légèrement rayé."
                    ),
                },
            ],
        ),
    ]


def seed() -> None:
    engine.dispose()  # libère les connexions (Windows refuse de supprimer un fichier ouvert)
    if DB_PATH.exists():
        DB_PATH.unlink()
    create_db_and_tables()

    templates = build_templates()
    with Session(engine) as session:
        for t in templates:
            session.add(t)
        for p in build_polices():
            session.add(p)
        session.commit()

        agents = build_agents(templates)
        for a in agents:
            session.add(a)
        session.commit()

        # Le pipeline P5 : 5 agents, la porte humaine, puis le courrier
        workflow = Workflow(
            nom="Sinistre auto — déclaration → règlement (P5)",
            etapes=[
                {"ordre": 0, "agent_id": agents[0].id, "type": "agent"},          # FNOL
                {"ordre": 1, "agent_id": agents[1].id, "type": "agent"},          # extraction
                {"ordre": 2, "agent_id": agents[2].id, "type": "agent"},          # gravité vision
                {"ordre": 3, "agent_id": agents[3].id, "type": "agent"},          # garanties (déterministe)
                {"ordre": 4, "agent_id": agents[4].id, "type": "agent"},          # indemnité (déterministe)
                {"ordre": 5, "agent_id": agents[5].id, "type": "porte_humaine"},  # HITL
                {"ordre": 6, "agent_id": agents[6].id, "type": "agent"},          # courrier
            ],
        )
        session.add(workflow)
        session.commit()

        for d in build_dossiers():
            session.add(d)
        session.commit()

    print(f"Seed OK -> {DB_PATH}")
    print("  3 templates, 6 polices, 7 agents, 1 workflow P5, 4 dossiers")
    print("  Dossier demo SIN-2026-001 : facture 2300 - vetuste 10% - franchise 220 = 1850 DT")
    print("  Dossier demo SIN-2026-004 : aucune piece chiffree -> porte 'demande_piece' (adaptation)")


if __name__ == "__main__":
    seed()
