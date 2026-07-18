"""Modèle de données Argus — version hackathon (CLAUDE.md section 6 + table Police).

Noms d'entités alignés sur le cahier des charges (M8.3), réduits au strict
nécessaire. Les champs structurés sont des colonnes JSON (SQLite les stocke
en texte, SQLAlchemy sérialise).
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


class Template(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nom: str
    categorie: str  # fnol | garanties | reglement (les 3 du scope)
    instructions_defaut: str
    garde_fous_defaut: dict = Field(default_factory=dict, sa_column=Column(JSON))


class Agent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nom: str
    categorie: str  # fnol | extraction | vision | garanties | indemnite | hitl | courrier
    template_id: Optional[int] = Field(default=None, foreign_key="template.id")
    instructions: str = ""
    # ex. {"seuil_validation": 1000, "plafond_auto": 500}
    seuils: dict = Field(default_factory=dict, sa_column=Column(JSON))
    # ex. {"deterministe": true, "bareme_vetuste": [...]}
    garde_fous: dict = Field(default_factory=dict, sa_column=Column(JSON))
    version: int = 1
    statut: str = "draft"  # draft | live


class Workflow(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nom: str
    statut: str = "live"
    # [{"ordre": 0, "agent_id": 1, "type": "agent"}, ..., {"ordre": 5, "agent_id": 6, "type": "porte_humaine"}]
    etapes: list = Field(default_factory=list, sa_column=Column(JSON))


class Police(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    numero: str
    assure_nom: str
    formule: str  # tiers | tous_risques
    # {"collision": {"plafond": 30000, "franchise": 220}, "bris_glace": {...}, ...}
    garanties: dict = Field(default_factory=dict, sa_column=Column(JSON))
    prime_payee: bool = True
    # {"marque": ..., "modele": ..., "immatriculation": ..., "annee": 2022}
    vehicule: dict = Field(default_factory=dict, sa_column=Column(JSON))


class Dossier(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ref: str
    branche: str = "auto"
    police_id: int = Field(foreign_key="police.id")
    workflow_id: Optional[int] = Field(default=None, foreign_key="workflow.id")
    declaration_texte: str  # texte libre FR/darija, entrée de l'agent FNOL
    etat: str = "recu"  # recu | en_cours | attente_validation | regle | refuse | cloture
    etape_courante: int = 0  # curseur dans workflow.etapes
    donnees_fnol: dict = Field(default_factory=dict, sa_column=Column(JSON))
    gravite: Optional[str] = None  # leger | moyen | lourd
    position_couverture: dict = Field(default_factory=dict, sa_column=Column(JSON))
    montant_recommande: Optional[float] = None
    montant_valide: Optional[float] = None  # écrit UNIQUEMENT par une décision humaine
    # [{"type": "constat", "chemin": "docs/samples/constat.jpg", "extraction": {...}}]
    pieces: list = Field(default_factory=list, sa_column=Column(JSON))
    cree_le: datetime = Field(default_factory=now)


class Run(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    dossier_id: int = Field(foreign_key="dossier.id")
    agent_id: int = Field(foreign_key="agent.id")
    entrees: dict = Field(default_factory=dict, sa_column=Column(JSON))
    sorties: dict = Field(default_factory=dict, sa_column=Column(JSON))
    statut: str = "succes"  # succes | echec
    confiance: Optional[float] = None
    cout: float = 0.0  # coût LLM en $ (0 pour les agents déterministes)
    duree_ms: int = 0
    horodatage: datetime = Field(default_factory=now)


class Tache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    dossier_id: int = Field(foreign_key="dossier.id")
    type: str = "validation_reglement"
    etat: str = "en_attente"  # en_attente | decidee
    montant: float
    # synthèse présentée au gestionnaire : faits, garanties, gravité, calcul détaillé
    proposition: dict = Field(default_factory=dict, sa_column=Column(JSON))
    decision: Optional[str] = None  # approuver | modifier | refuser
    motif: Optional[str] = None
    validateur: Optional[str] = None
    cree_le: datetime = Field(default_factory=now)
    decide_le: Optional[datetime] = None


class EvenementAudit(SQLModel, table=True):
    """Append-only : aucun endpoint UPDATE/DELETE ne doit exister sur cette table."""

    id: Optional[int] = Field(default=None, primary_key=True)
    acteur: str  # "agent:moteur_garanties v1" | "humain:superviseur"
    acteur_type: str  # agent | humain
    type: str  # run_agent | decision_humaine | changement_etat | creation_agent
    objet: str  # "dossier:SIN-2026-001" | "agent:7"
    avant: dict = Field(default_factory=dict, sa_column=Column(JSON))
    apres: dict = Field(default_factory=dict, sa_column=Column(JSON))
    motif: Optional[str] = None
    horodatage: datetime = Field(default_factory=now)
