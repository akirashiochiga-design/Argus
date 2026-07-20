"""Adaptateurs démo — ERP / SI métier du marché assurance Tunisie.

Simulations locales clairement étiquetées : aucun appel réseau, aucun credential.
Chaque pack expose le même contrat Connecteur (tester / synchroniser) pour
pousser vers le cœur métier les dossiers déjà validés par un humain.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from ..audit import tracer
from ..models import Dossier, EvenementAudit


# Catalogue marché TN — cœurs métier / SI sinistres réellement présents chez les assureurs.
SYSTEMES_ERP_TN: list[dict] = [
    {
        "identifiant": "digiclaim",
        "nom": "DigiClaim",
        "editeur": "Avidea",
        "porte": "API REST",
        "role": "Gestion sinistres digitale",
        "compagnies": ["Maghrebia", "COMAR", "GAT"],
    },
    {
        "identifiant": "micard",
        "nom": "MiCard",
        "editeur": "Avidea",
        "porte": "API REST",
        "role": "Carte / tiers payant santé",
        "compagnies": ["Maghrebia", "ASTREE"],
    },
    {
        "identifiant": "pass",
        "nom": "Pass Insurance",
        "editeur": "RGI",
        "porte": "Web services",
        "role": "Cœur métier multi-branches",
        "compagnies": ["STAR", "COMAR"],
    },
    {
        "identifiant": "proassur",
        "nom": "PROASSUR",
        "editeur": "EDI Tunisie",
        "porte": "Web services",
        "role": "Production & sinistres",
        "compagnies": ["Assurances locales"],
    },
    {
        "identifiant": "erecours",
        "nom": "e-Recours",
        "editeur": "FTUSA",
        "porte": "Portail",
        "role": "Recours inter-compagnies",
        "compagnies": ["Toutes FTUSA"],
    },
]


def _deja_pousse(session: Session, connecteur_id: str, dossier_ref: str) -> bool:
    evenements = session.exec(
        select(EvenementAudit).where(
            EvenementAudit.type == "synchronisation_erp_marche",
            EvenementAudit.objet == f"dossier:{dossier_ref}",
        )
    ).all()
    return any(
        (ev.apres or {}).get("connecteur") == connecteur_id for ev in evenements
    )


class ConnecteurERPMarcheTN:
    """Adaptateur simulé vers un SI / ERP du marché tunisien."""

    direction = "sortant"
    protocole = "simulation"
    marche = "tunisie"

    def __init__(self, definition: dict):
        self.identifiant = definition["identifiant"]
        self.nom = definition["nom"]
        self.editeur = definition["editeur"]
        self.porte = definition["porte"]
        self.role = definition["role"]
        self.compagnies = list(definition.get("compagnies") or [])

    def tester(self) -> dict:
        return {
            "identifiant": self.identifiant,
            "nom": self.nom,
            "editeur": self.editeur,
            "porte": self.porte,
            "role": self.role,
            "compagnies": self.compagnies,
            "direction": self.direction,
            "protocole": self.protocole,
            "marche": self.marche,
            "simulation": True,
            "mode": "écriture métier après validation humaine",
            "latence_ms": 18,
            "ok": True,
        }

    def synchroniser(self, session: Session) -> dict:
        """Pousse les dossiers validés vers le SI cible (ACK simulé + audit)."""
        dossiers = session.exec(
            select(Dossier).where(Dossier.montant_valide != None)  # noqa: E711
        ).all()
        pousses: list[dict] = []
        ignores = 0
        for dossier in dossiers:
            if _deja_pousse(session, self.identifiant, dossier.ref):
                ignores += 1
                continue
            payload = {
                "reference_sinistre": dossier.ref,
                "montant_valide": dossier.montant_valide,
                "devise": "TND",
                "etat_norix": dossier.etat,
                "systeme_cible": self.nom,
                "editeur": self.editeur,
                "porte": self.porte,
                "accuse_le": datetime.now(timezone.utc).isoformat(),
            }
            tracer(
                session,
                acteur=f"systeme:erp_tn:{self.identifiant}",
                acteur_type="agent",
                type="synchronisation_erp_marche",
                objet=f"dossier:{dossier.ref}",
                apres={
                    "connecteur": self.identifiant,
                    "systeme": self.nom,
                    "montant": dossier.montant_valide,
                    "simulation": True,
                    "payload": payload,
                },
                motif=(
                    f"Accusé de réception — {self.nom} ({self.editeur}) "
                    "après validation humaine"
                ),
            )
            pousses.append(
                {
                    "dossier_ref": dossier.ref,
                    "montant": dossier.montant_valide,
                }
            )
        session.commit()
        return {
            "statut": "succes",
            "connecteur": self.identifiant,
            "systeme": self.nom,
            "editeur": self.editeur,
            "dossiers_pushes": len(pousses),
            "dossiers_ignores": ignores,
            "detail": pousses,
            "simulation": True,
            "protocole": self.protocole,
        }


def construire_tous() -> list[ConnecteurERPMarcheTN]:
    return [ConnecteurERPMarcheTN(definition) for definition in SYSTEMES_ERP_TN]
