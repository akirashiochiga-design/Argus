"""Marketplace : publication de templates, achat ou location dans le Studio."""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from .. import marketplace_qa
from ..agents.tools import noms_pour
from ..audit import tracer
from ..db import get_session
from ..models import Agent, MarketplaceInstallation, MarketplaceListing


router = APIRouter(prefix="/marketplace", tags=["marketplace"])

CATEGORIES_AUTORISEES = {"fnol", "extraction", "vision", "courrier", "assistant"}
DUREE_LOCATION_DEFAUT = 30


class SoumissionTemplate(BaseModel):
    nom: str = Field(min_length=3, max_length=100)
    categorie: str
    editeur: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=20, max_length=600)
    prix: float = Field(default=0, ge=0)
    prix_location: float = Field(default=0, ge=0)
    tags: list[str] = Field(default_factory=list)
    instructions: str = Field(min_length=30, max_length=4000)
    seuils: dict = Field(default_factory=dict)


class DemandeInstallation(BaseModel):
    mode: str = Field(default="achat", pattern="^(achat|location)$")
    duree_jours: int = Field(default=DUREE_LOCATION_DEFAUT, ge=1, le=365)


class ModificationListing(BaseModel):
    nom: Optional[str] = Field(default=None, min_length=3, max_length=100)
    description: Optional[str] = Field(default=None, min_length=20, max_length=600)
    prix: Optional[float] = Field(default=None, ge=0)
    prix_location: Optional[float] = Field(default=None, ge=0)
    tags: Optional[list[str]] = None
    instructions: Optional[str] = Field(default=None, min_length=30, max_length=4000)
    seuils: Optional[dict] = None


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


def _location_expiree(installation: MarketplaceInstallation) -> bool:
    return (
        installation.type_acquisition == "location"
        and installation.expire_le is not None
        and installation.expire_le < datetime.utcnow()
    )


def _appliquer_expiration(session: Session, installation: MarketplaceInstallation) -> Agent | None:
    """Désactive réactivement un agent loué dont l'abonnement n'a pas été renouvelé."""
    agent = session.get(Agent, installation.agent_id)
    if not agent:
        return None
    if _location_expiree(installation) and agent.statut == "live":
        agent.statut = "draft"
        session.add(agent)
        tracer(
            session,
            acteur="systeme:marketplace",
            acteur_type="agent",
            type="location_expiree",
            objet=f"agent:{agent.id}",
            avant={"statut": "live"},
            apres={"statut": "draft", "expire_le": installation.expire_le.isoformat()},
            motif="Abonnement de location expiré et non renouvelé — agent désactivé",
        )
        session.commit()
        session.refresh(agent)
    return agent


def _etat_installation(installation: MarketplaceInstallation | None) -> dict | None:
    if not installation:
        return None
    if installation.type_acquisition != "location":
        return {
            "installation_id": installation.id,
            "type_acquisition": "achat",
            "expire_le": None,
            "jours_restants": None,
            "expiree": False,
        }
    expiree = _location_expiree(installation)
    jours_restants = None
    if installation.expire_le:
        delta = installation.expire_le - datetime.utcnow()
        jours_restants = max(0, delta.days)
    return {
        "installation_id": installation.id,
        "type_acquisition": "location",
        "expire_le": installation.expire_le,
        "jours_restants": jours_restants,
        "expiree": expiree,
        "renouvellements": installation.renouvellements,
    }


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
        if installation:
            _appliquer_expiration(session, installation)
        resultat.append(
            {
                **listing.model_dump(),
                "installe": installation is not None,
                "agent_id": installation.agent_id if installation else None,
                "location": _etat_installation(installation),
            }
        )
    return resultat


@router.get("/installations")
def lister_installations(
    acheteur: str = "compagnie_demo",
    session: Session = Depends(get_session),
) -> list[dict]:
    """Vue "mes agents" : tous les agents achetés ou loués par la compagnie."""
    installations = session.exec(
        select(MarketplaceInstallation).where(MarketplaceInstallation.acheteur == acheteur)
    ).all()
    resultat = []
    for installation in installations:
        _appliquer_expiration(session, installation)
        listing = session.get(MarketplaceListing, installation.listing_id)
        agent = session.get(Agent, installation.agent_id)
        resultat.append(
            {
                "installation_id": installation.id,
                "listing_id": installation.listing_id,
                "listing_nom": listing.nom if listing else None,
                "editeur": listing.editeur if listing else None,
                "agent_id": installation.agent_id,
                "agent_statut": agent.statut if agent else None,
                **_etat_installation(installation),
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
    corps: DemandeInstallation = DemandeInstallation(),
    session: Session = Depends(get_session),
) -> dict:
    listing = session.get(MarketplaceListing, listing_id)
    if not listing or listing.statut != "publie":
        raise HTTPException(404, "Agent Marketplace introuvable")
    if corps.mode == "location" and listing.prix_location <= 0:
        raise HTTPException(422, "Cet agent n'est pas proposé à la location")

    existante = _installation(session, listing_id)
    if existante:
        _appliquer_expiration(session, existante)
        if existante.type_acquisition == "achat" or not _location_expiree(existante):
            agent = session.get(Agent, existante.agent_id)
            return {
                "listing": listing,
                "agent": agent,
                "deja_installe": True,
                "location": _etat_installation(existante),
            }
        # Location expirée : on la renouvelle au lieu de dupliquer l'installation.
        return _renouveler_installation(session, existante, corps.duree_jours, motif_renouvellement=False)

    expire_le = (
        datetime.utcnow() + timedelta(days=corps.duree_jours)
        if corps.mode == "location"
        else None
    )
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
    installation = MarketplaceInstallation(
        listing_id=listing.id,
        agent_id=agent.id,
        type_acquisition=corps.mode,
        duree_jours=corps.duree_jours if corps.mode == "location" else None,
        expire_le=expire_le,
    )
    session.add(installation)
    if corps.mode == "location":
        listing.locations_actives += 1
        prix_affiche = f"{listing.prix_location} DT/mois"
    else:
        listing.installations += 1
        prix_affiche = f"{listing.prix} DT"
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
            "type_acquisition": corps.mode,
            "prix": prix_affiche,
            **({"expire_le": expire_le.isoformat()} if expire_le else {}),
        },
        motif=(
            f"Agent loué pour {corps.duree_jours} jours et prêt à l'emploi dans le Studio"
            if corps.mode == "location"
            else "Agent acheté et prêt à l'emploi dans le Studio"
        ),
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
        return {
            "listing": listing,
            "agent": agent,
            "deja_installe": True,
            "location": _etat_installation(existante),
        }
    session.refresh(agent)
    session.refresh(listing)
    session.refresh(installation)
    return {
        "listing": listing,
        "agent": agent,
        "deja_installe": False,
        "location": _etat_installation(installation),
    }


def _renouveler_installation(
    session: Session,
    installation: MarketplaceInstallation,
    duree_jours: int,
    *,
    motif_renouvellement: bool = True,
) -> dict:
    agent = session.get(Agent, installation.agent_id)
    listing = session.get(MarketplaceListing, installation.listing_id)
    if not agent or not listing:
        raise HTTPException(404, "Installation introuvable")
    base = (
        installation.expire_le
        if installation.expire_le and installation.expire_le > datetime.utcnow()
        else datetime.utcnow()
    )
    reactivation = agent.statut != "live"
    installation.expire_le = base + timedelta(days=duree_jours)
    installation.duree_jours = duree_jours
    installation.renouvellements += 1
    agent.statut = "live"
    session.add(installation)
    session.add(agent)
    tracer(
        session,
        acteur="humain:responsable_sinistres",
        acteur_type="humain",
        type="renouvellement_location_marketplace",
        objet=f"agent:{agent.id}",
        avant={"statut": "draft" if reactivation else "live"},
        apres={
            "statut": "live",
            "expire_le": installation.expire_le.isoformat(),
            "renouvellements": installation.renouvellements,
        },
        motif=(
            f"Location renouvelée pour {duree_jours} jours après expiration — agent réactivé"
            if reactivation
            else f"Location renouvelée pour {duree_jours} jours supplémentaires"
        ),
    )
    session.commit()
    session.refresh(installation)
    session.refresh(agent)
    session.refresh(listing)
    return {
        "listing": listing,
        "agent": agent,
        "deja_installe": True,
        "location": _etat_installation(installation),
    }


class DemandeRenouvellement(BaseModel):
    duree_jours: int = Field(default=DUREE_LOCATION_DEFAUT, ge=1, le=365)


@router.post("/installations/{installation_id}/renouveler")
def renouveler_installation(
    installation_id: int,
    corps: DemandeRenouvellement = DemandeRenouvellement(),
    session: Session = Depends(get_session),
) -> dict:
    installation = session.get(MarketplaceInstallation, installation_id)
    if not installation:
        raise HTTPException(404, "Installation introuvable")
    if installation.type_acquisition != "location":
        raise HTTPException(422, "Seule une location peut être renouvelée")
    return _renouveler_installation(session, installation, corps.duree_jours)


def _resume_echecs(rapport: dict) -> str:
    echecs = [t["detail"] for t in rapport["tests"] if t["statut"] == "echec"]
    return " · ".join(echecs)


def _appliquer_verdict_qa(session: Session, listing: MarketplaceListing) -> dict:
    """Fait passer la suite de tests Norix et fixe seule le statut — jamais un humain,
    ni côté éditeur ni côté compagnie (cette décision est celle de Norix, cf. CLAUDE.md §3)."""
    rapport = marketplace_qa.executer(
        session,
        nom=listing.nom,
        description=listing.description,
        instructions=listing.instructions,
        categorie=listing.categorie,
        garde_fous=listing.garde_fous,
    )
    listing.derniere_revue = rapport
    if rapport["resultat"] == "valide":
        listing.statut = "publie"
        listing.verifie = True
        listing.motif_refus = None
    else:
        listing.statut = "refuse"
        listing.verifie = False
        listing.motif_refus = _resume_echecs(rapport)
    tracer(
        session,
        acteur="systeme:qa_marketplace",
        acteur_type="agent",
        type="controle_automatique_marketplace",
        objet=f"listing:{listing.id}",
        apres={"statut": listing.statut, "tests": rapport["tests"]},
        motif=(
            "Tous les tests automatiques Norix ont réussi — agent publié"
            if rapport["resultat"] == "valide"
            else f"Tests automatiques échoués : {listing.motif_refus}"
        ),
    )
    return rapport


@router.post("/listings", status_code=201)
def soumettre_listing(
    corps: SoumissionTemplate,
    session: Session = Depends(get_session),
) -> MarketplaceListing:
    if corps.categorie not in CATEGORIES_AUTORISEES:
        raise HTTPException(422, "Catégorie d'agent non autorisée")
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
        prix_location=corps.prix_location,
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
        apres={"nom": listing.nom, "categorie": listing.categorie, "prix": listing.prix},
        motif="Agent soumis aux tests automatiques Norix",
    )
    _appliquer_verdict_qa(session, listing)
    session.add(listing)
    session.commit()
    session.refresh(listing)
    return listing


@router.patch("/listings/{listing_id}")
def modifier_listing(
    listing_id: int,
    corps: ModificationListing,
    session: Session = Depends(get_session),
) -> MarketplaceListing:
    """Un éditeur corrige son annonce avant publication, ou après un refus.

    Impossible une fois publié : des compagnies ont pu déjà l'installer telle
    quelle, une modification silencieuse romprait la trace de ce qu'elles ont
    réellement acheté. Une évolution post-publication est une nouvelle annonce.
    Toute modification refait passer l'annonce par les tests automatiques Norix.
    """
    listing = session.get(MarketplaceListing, listing_id)
    if not listing:
        raise HTTPException(404, "Agent soumis introuvable")
    if listing.statut == "publie":
        raise HTTPException(
            409,
            "Cet agent est déjà publié — des compagnies l'ont peut-être installé tel "
            "quel. Soumettez une nouvelle annonce pour une évolution.",
        )

    avant = {"nom": listing.nom, "prix": listing.prix, "statut": listing.statut}
    if corps.nom is not None:
        nouveau_nom = corps.nom.strip()
        doublon = session.exec(
            select(MarketplaceListing).where(
                MarketplaceListing.nom == nouveau_nom,
                MarketplaceListing.editeur == listing.editeur,
                MarketplaceListing.id != listing.id,
            )
        ).first()
        if doublon:
            raise HTTPException(409, "Cet éditeur a déjà soumis un agent portant ce nom")
        listing.nom = nouveau_nom
    if corps.description is not None:
        listing.description = corps.description.strip()
    if corps.prix is not None:
        listing.prix = corps.prix
    if corps.prix_location is not None:
        listing.prix_location = corps.prix_location
    if corps.tags is not None:
        listing.tags = corps.tags[:6]
    if corps.instructions is not None:
        listing.instructions = corps.instructions.strip()
    if corps.seuils is not None:
        listing.seuils = corps.seuils

    session.add(listing)
    tracer(
        session,
        acteur=f"humain:editeur_{listing.editeur.lower().replace(' ', '_')}",
        acteur_type="humain",
        type="modification_marketplace",
        objet=f"listing:{listing.id}",
        avant=avant,
        apres={"nom": listing.nom, "prix": listing.prix},
        motif="Annonce corrigée, resoumise aux tests automatiques Norix",
    )
    _appliquer_verdict_qa(session, listing)
    session.add(listing)
    session.commit()
    session.refresh(listing)
    return listing
