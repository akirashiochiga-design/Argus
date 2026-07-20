"""File sortante locale représentant l'ERP financier interne d'un assureur."""
from datetime import datetime, timezone

from sqlmodel import Session, select

from ..audit import tracer
from ..models import Dossier, EcritureERP


class ConnecteurERPDemo:
    identifiant = "erp_interne_demo"
    nom = "ERP Finance interne"
    direction = "sortant"

    def tester(self) -> dict:
        return {
            "identifiant": self.identifiant,
            "nom": self.nom,
            "direction": self.direction,
            "protocole": "REST / SOAP / SQL (simulé localement)",
            "mode": "écriture après validation humaine",
            "latence_ms": 18,
            "simulation": True,
        }

    def synchroniser(self, session: Session) -> dict:
        ecritures = session.exec(
            select(EcritureERP).where(
                EcritureERP.connecteur == self.identifiant,
                EcritureERP.statut == "planifiee",
            )
        ).all()
        for ecriture in ecritures:
            ecriture.statut = "envoyee"
            ecriture.envoyee_le = datetime.now(timezone.utc)
            session.add(ecriture)
            dossier = session.get(Dossier, ecriture.dossier_id)
            tracer(
                session,
                acteur="systeme:connecteur_erp_interne",
                acteur_type="agent",
                type="ecriture_erp_envoyee",
                objet=f"dossier:{dossier.ref if dossier else ecriture.dossier_id}",
                avant={"statut": "planifiee"},
                apres={
                    "statut": "envoyee",
                    "montant": ecriture.montant,
                    "connecteur": self.identifiant,
                },
                motif="Accusé de réception du SI interne simulé après validation humaine",
            )
        session.commit()
        return {
            "statut": "succes",
            "ecritures_envoyees": len(ecritures),
            "simulation": True,
        }


def planifier_ecriture(
    session: Session,
    dossier: Dossier,
    validateur: str,
) -> EcritureERP | None:
    """Créer une seule écriture, uniquement si un humain a validé un montant."""
    if dossier.montant_valide is None:
        return None
    existante = session.exec(
        select(EcritureERP).where(EcritureERP.dossier_id == dossier.id)
    ).first()
    if existante:
        return existante
    ecriture = EcritureERP(
        dossier_id=dossier.id,
        montant=dossier.montant_valide,
        payload={
            "reference_sinistre": dossier.ref,
            "montant_valide": dossier.montant_valide,
            "devise": "TND",
            "valide_par": validateur,
        },
    )
    session.add(ecriture)
    session.flush()
    tracer(
        session,
        acteur=f"humain:{validateur}",
        acteur_type="humain",
        type="ecriture_erp_planifiee",
        objet=f"dossier:{dossier.ref}",
        apres={
            "ecriture_id": ecriture.id,
            "montant": ecriture.montant,
            "connecteur": ecriture.connecteur,
            "statut": ecriture.statut,
        },
        motif="Écriture préparée après validation explicite du gestionnaire",
    )
    session.commit()
    session.refresh(ecriture)
    return ecriture
