"""Adaptateur local représentant une bibliothèque SharePoint de sinistres."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

from ..audit import tracer
from ..models import Dossier


RACINE = Path(__file__).resolve().parents[3]
MANIFESTE = RACINE / "docs" / "inbox" / "sharepoint-manifest.json"


class ConnecteurDocumentsLocal:
    identifiant = "sharepoint_demo"
    nom = "SharePoint Sinistres"
    direction = "entrant"

    def _manifeste(self) -> dict:
        if not MANIFESTE.exists():
            raise FileNotFoundError("Manifeste SharePoint introuvable")
        donnees = json.loads(MANIFESTE.read_text(encoding="utf-8"))
        for document in donnees.get("documents", []):
            if not (RACINE / document["chemin"]).exists():
                raise FileNotFoundError(f"Document source introuvable : {document['chemin']}")
        return donnees

    def tester(self) -> dict:
        debut = time.monotonic()
        donnees = self._manifeste()
        return {
            "identifiant": self.identifiant,
            "nom": self.nom,
            "source": donnees["source"],
            "tenant": donnees["tenant"],
            "dossier": donnees["dossier"],
            "direction": self.direction,
            "documents_disponibles": len(donnees.get("documents", [])),
            "latence_ms": int((time.monotonic() - debut) * 1000),
        }

    def synchroniser(self, session: Session) -> dict:
        debut = time.monotonic()
        donnees = self._manifeste()
        importes = 0
        ignores = 0
        introuvables = []
        for document in donnees.get("documents", []):
            dossier = session.exec(
                select(Dossier).where(Dossier.ref == document["dossier_ref"])
            ).first()
            if not dossier:
                introuvables.append(document["dossier_ref"])
                continue
            deja_present = any(
                piece.get("source_nom") == document["nom_source"]
                and piece.get("source_connecteur") == self.identifiant
                for piece in dossier.pieces
            )
            if deja_present:
                ignores += 1
                continue
            dossier.pieces = [
                *dossier.pieces,
                {
                    "type": document["type"],
                    "chemin": document["chemin"],
                    "source_connecteur": self.identifiant,
                    "source_nom": document["nom_source"],
                    "recu_le": document.get("recu_le") or datetime.now(timezone.utc).isoformat(),
                    **({"montant": document["montant"]} if document.get("montant") is not None else {}),
                },
            ]
            session.add(dossier)
            importes += 1

        resultat = {
            "statut": "succes",
            "source": donnees["source"],
            "documents_importes": importes,
            "documents_ignores": ignores,
            "dossiers_introuvables": sorted(set(introuvables)),
            "duree_ms": int((time.monotonic() - debut) * 1000),
            "horodatage": datetime.now(timezone.utc).isoformat(),
        }
        # La file d'approbation interroge régulièrement le connecteur. On ne
        # pollue pas l'audit avec les vérifications qui n'ont rien importé.
        if importes:
            tracer(
                session,
                acteur="systeme:connecteur_sharepoint",
                acteur_type="agent",
                type="synchronisation_documents",
                objet=f"integration:{self.identifiant}",
                apres=resultat,
                motif="Import idempotent depuis la bibliothèque SharePoint Sinistres",
            )
        session.commit()
        return resultat


def lister_documents() -> dict:
    if not MANIFESTE.exists():
        return {
            "source": "SharePoint Sinistres",
            "tenant": "Horizon Assurances",
            "dossier": "Sinistres Auto / 2026",
            "documents": [],
        }
    donnees = json.loads(MANIFESTE.read_text(encoding="utf-8"))
    return {
        "source": donnees.get("source", "SharePoint Sinistres"),
        "tenant": donnees.get("tenant"),
        "dossier": donnees.get("dossier"),
        "documents": donnees.get("documents", []),
    }


def ajouter_document(corps: dict) -> dict:
    """Ajoute un fichier dans la bibliothèque SharePoint (manifeste local)."""
    dossier_ref = (corps.get("dossier_ref") or "").strip()
    type_piece = (corps.get("type") or "photo_expertise").strip()
    chemin = (corps.get("chemin") or "docs/samples/degats-3.jpg").strip()
    nom_source = (corps.get("nom_source") or "").strip()
    if not dossier_ref:
        raise ValueError("Référence dossier requise")
    if not (RACINE / chemin).exists():
        raise FileNotFoundError(f"Fichier introuvable : {chemin}")
    if not nom_source:
        nom_source = f"{type_piece}-{dossier_ref.lower()}-{int(time.time())}.jpg"

    donnees = lister_documents()
    document = {
        "dossier_ref": dossier_ref,
        "type": type_piece,
        "chemin": chemin,
        "nom_source": nom_source,
        "recu_le": datetime.now(timezone.utc).isoformat(),
    }
    if corps.get("montant") not in (None, ""):
        document["montant"] = float(corps["montant"])
    donnees["documents"] = [*donnees.get("documents", []), document]
    MANIFESTE.parent.mkdir(parents=True, exist_ok=True)
    MANIFESTE.write_text(
        json.dumps(donnees, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return document
