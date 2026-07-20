"""Marketplace : publication de templates et installation immédiate dans le Studio."""
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..agents.tools import noms_pour
from ..audit import tracer
from ..db import get_session
from ..models import Agent, MarketplaceInstallation, MarketplaceListing


router = APIRouter(prefix="/marketplace", tags=["marketplace"])

CATEGORIES_AUTORISEES = {"fnol", "extraction", "vision", "courrier", "assistant"}
MOTIFS_SECRET = re.compile(
    r"(api[_ -]?key|mot[_ -]?de[_ -]?passe|password|secret|sk-[a-z0-9_-]{8,})",
    re.IGNORECASE,
)


class SoumissionTemplate(BaseModel):
    nom: str = Field(min_length=3, max_length=100)
    categorie: str
    editeur: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=20, max_length=600)
    prix: float = Field(default=0, ge=0)
    tags: list[str] = Field(default_factory=list)
    instructions: str = Field(min_length=30, max_length=4000)
    seuils: dict = Field(default_factory=dict)


def _installation(
    session: Session,
    listing_id: int,
    acheteur: str = "compagnie_demo",
) -> MarketplaceInstallation | None:
    return session.exec(
        select(MarketplaceInstallation).where(
            MarketplaceInstallation.listing_id == listing_id,
            MarketplaceInstallation.acheteur == acheteur,
        )
    ).first()


@router.get("/listings")
def lister_listings(session: Session = Depends(get_session)) -> list[dict]:
    listings = session.exec(
        select(MarketplaceListing)
        .where(MarketplaceListing.statut == "publie")
        .order_by(MarketplaceListing.installations.desc())
    ).all()
    resultat = []
    for listing in listings:
        installation = _installation(session, listing.id)
        resultat.append(
            {
                **listing.model_dump(),
                "installe": installation is not None,
                "agent_id": installation.agent_id if installation else None,
            }
        )
    return resultat


@router.get("/editeurs/{editeur}/listings")
def lister_listings_editeur(
    editeur: str,
    session: Session = Depends(get_session),
) -> list[MarketplaceListing]:
    """Tableau de bord des templates publiés par un éditeur."""
    return session.exec(
        select(MarketplaceListing)
        .where(MarketplaceListing.editeur == editeur)
        .order_by(MarketplaceListing.id.desc())
    ).all()


@router.post("/listings/{listing_id}/installer")
def installer_listing(
    listing_id: int,
    session: Session = Depends(get_session),
) -> dict:
    listing = session.get(MarketplaceListing, listing_id)
    if not listing or listing.statut != "publie":
        raise HTTPException(404, "Agent Marketplace introuvable")

    existante = _installation(session, listing_id)
    if existante:
        agent = session.get(Agent, existante.agent_id)
        return {"listing": listing, "agent": agent, "deja_installe": True}

    agent = Agent(
        nom=listing.nom,
        categorie=listing.categorie,
        instructions=listing.instructions,
        seuils=listing.seuils,
        garde_fous={
            **listing.garde_fous,
            "pas_de_decision_argent": True,
            "origine": "marketplace",
            "listing_id": listing.id,
            "editeur": listing.editeur,
            "outils_autorises": listing.garde_fous.get(
                "outils_autorises",
                noms_pour(listing.categorie),
            ),
        },
        statut="live",
    )
    session.add(agent)
    session.flush()
    session.add(
        MarketplaceInstallation(
            listing_id=listing.id,
            agent_id=agent.id,
        )
    )
    listing.installations += 1
    session.add(listing)
    tracer(
        session,
        acteur="humain:responsable_sinistres",
        acteur_type="humain",
        type="installation_marketplace",
        objet=f"agent:{agent.id}",
        apres={
            "listing_id": listing.id,
            "nom": agent.nom,
            "editeur": listing.editeur,
            "statut": "live",
        },
        motif="Agent acheté et prêt à l'emploi dans le Studio",
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existante = _installation(session, listing_id)
        if not existante:
            raise
        agent = session.get(Agent, existante.agent_id)
        listing = session.get(MarketplaceListing, listing_id)
        return {"listing": listing, "agent": agent, "deja_installe": True}
    session.refresh(agent)
    session.refresh(listing)
    return {"listing": listing, "agent": agent, "deja_installe": False}


@router.post("/listings", status_code=201)
def soumettre_listing(
    corps: SoumissionTemplate,
    session: Session = Depends(get_session),
) -> MarketplaceListing:
    if corps.categorie not in CATEGORIES_AUTORISEES:
        raise HTTPException(422, "Catégorie d'agent non autorisée")
    if MOTIFS_SECRET.search(corps.instructions):
        raise HTTPException(422, "Retirez les clés, mots de passe ou secrets des instructions")
    doublon = session.exec(
        select(MarketplaceListing).where(
            MarketplaceListing.nom == corps.nom.strip(),
            MarketplaceListing.editeur == corps.editeur.strip(),
        )
    ).first()
    if doublon:
        raise HTTPException(409, "Cet éditeur a déjà soumis un agent portant ce nom")

    listing = MarketplaceListing(
        nom=corps.nom.strip(),
        categorie=corps.categorie,
        editeur=corps.editeur.strip(),
        description=corps.description.strip(),
        prix=corps.prix,
        tags=corps.tags[:6],
        instructions=corps.instructions.strip(),
        garde_fous={
            "pas_de_decision_argent": True,
            "outils_autorises": noms_pour(corps.categorie),
            "max_iterations_agent": 4,
        },
        seuils=corps.seuils,
        statut="en_attente",
        verifie=False,
    )
    session.add(listing)
    session.flush()
    tracer(
        session,
        acteur=f"humain:editeur_{listing.editeur.lower().replace(' ', '_')}",
        acteur_type="humain",
        type="soumission_marketplace",
        objet=f"listing:{listing.id}",
        apres={
            "nom": listing.nom,
            "categorie": listing.categorie,
            "prix": listing.prix,
            "statut": listing.statut,
        },
        motif="Agent soumis à la revue Argus avant publication",
    )
    session.commit()
    session.refresh(listing)
    return listing


@router.post("/listings/{listing_id}/valider")
def valider_listing(
    listing_id: int,
    session: Session = Depends(get_session),
) -> MarketplaceListing:
    """Revue Argus : contrôles automatiques puis publication du template."""
    listing = session.get(MarketplaceListing, listing_id)
    if not listing:
        raise HTTPException(404, "Agent soumis introuvable")
    if listing.statut != "en_attente":
        raise HTTPException(409, "Cet agent a déjà été revu")
    listing.statut = "publie"
    listing.verifie = True
    session.add(listing)
    tracer(
        session,
        acteur="humain:comite_argus",
        acteur_type="humain",
        type="validation_marketplace",
        objet=f"listing:{listing.id}",
        avant={"statut": "en_attente"},
        apres={"statut": "publie", "verifie": True},
        motif="Contrôles automatiques réussis — agent approuvé et publié",
    )
    session.commit()
    session.refresh(listing)
    return listing
