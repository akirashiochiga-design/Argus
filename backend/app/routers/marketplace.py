"""Marketplace : publication de templates, achat ou location dans le Studio."""
import re
from datetime import datetime, timedelta

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
        apres={
            "nom": listing.nom,
            "categorie": listing.categorie,
            "prix": listing.prix,
            "statut": listing.statut,
        },
        motif="Agent soumis à la revue Norix avant publication",
    )
    session.commit()
    session.refresh(listing)
    return listing


@router.post("/listings/{listing_id}/valider")
def valider_listing(
    listing_id: int,
    session: Session = Depends(get_session),
) -> MarketplaceListing:
    """Revue Norix : contrôles automatiques puis publication du template."""
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
        acteur="humain:comite_norix",
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
