"""Adaptateur local — bibliothèque SharePoint de sinistres.

Flux démo :
1. Extraire des dossiers (dossiers + pièces) depuis SharePoint → Norix
2. Une fois traités, redéposer un retour (courrier / synthèse) dans SharePoint
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

from ..audit import tracer
from ..models import Dossier, Police
from ..workflow_service import traitement_actif


RACINE = Path(__file__).resolve().parents[3]
MANIFESTE = RACINE / "docs" / "inbox" / "sharepoint-manifest.json"

ETATS_TRAITES = {"regle", "refuse", "cloture"}


class ConnecteurDocumentsLocal:
    identifiant = "sharepoint_demo"
    nom = "SharePoint Sinistres"
    direction = "bidirectionnel"
    protocole = "local"  # MCP documentaire : à venir

    def _lire_brut(self) -> dict:
        if not MANIFESTE.exists():
            raise FileNotFoundError("Manifeste SharePoint introuvable")
        return json.loads(MANIFESTE.read_text(encoding="utf-8"))

    def _normaliser(self, donnees: dict) -> dict:
        """Accepte l'ancien format (documents plats) et le format dossiers."""
        dossiers = list(donnees.get("dossiers") or [])
        if not dossiers and donnees.get("documents"):
            # Migration douce de l'ancien manifeste plat
            par_ref: dict[str, dict] = {}
            for document in donnees["documents"]:
                ref = document["dossier_ref"]
                if ref not in par_ref:
                    par_ref[ref] = {
                        "ref": ref,
                        "police_numero": document.get("police_numero") or "",
                        "assure": document.get("assure") or "Assuré SharePoint",
                        "declaration": document.get("declaration")
                        or f"Dossier importé depuis SharePoint ({ref}).",
                        "type_sinistre": document.get("type_sinistre") or "collision",
                        "statut_sharepoint": "a_traiter",
                        "documents": [],
                    }
                piece = {
                    "type": document["type"],
                    "chemin": document["chemin"],
                    "nom_source": document["nom_source"],
                }
                if document.get("montant") is not None:
                    piece["montant"] = document["montant"]
                if document.get("recu_le"):
                    piece["recu_le"] = document["recu_le"]
                par_ref[ref]["documents"].append(piece)
            dossiers = list(par_ref.values())

        for dossier in dossiers:
            for document in dossier.get("documents", []):
                chemin = RACINE / document["chemin"]
                if not chemin.exists():
                    raise FileNotFoundError(
                        f"Document source introuvable : {document['chemin']}"
                    )
        return {
            "source": donnees.get("source", "SharePoint Sinistres"),
            "tenant": donnees.get("tenant", "Horizon Assurances"),
            "bibliotheque": donnees.get("bibliotheque")
            or donnees.get("dossier")
            or "Sinistres Auto / 2026",
            "dossiers": dossiers,
            "retours": list(donnees.get("retours") or []),
        }

    def _manifeste(self) -> dict:
        return self._normaliser(self._lire_brut())

    def _ecrire(self, donnees: dict) -> None:
        MANIFESTE.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "source": donnees.get("source", "SharePoint Sinistres"),
            "tenant": donnees.get("tenant", "Horizon Assurances"),
            "bibliotheque": donnees.get("bibliotheque", "Sinistres Auto / 2026"),
            "dossiers": donnees.get("dossiers", []),
            "retours": donnees.get("retours", []),
        }
        MANIFESTE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def tester(self) -> dict:
        debut = time.monotonic()
        donnees = self._manifeste()
        docs = sum(len(d.get("documents", [])) for d in donnees["dossiers"])
        return {
            "identifiant": self.identifiant,
            "nom": self.nom,
            "source": donnees["source"],
            "tenant": donnees["tenant"],
            "bibliotheque": donnees["bibliotheque"],
            "direction": self.direction,
            "protocole": self.protocole,
            "mcp": "à venir",
            "dossiers_disponibles": len(donnees["dossiers"]),
            "documents_disponibles": docs,
            "retours_deposes": len(donnees["retours"]),
            "latence_ms": int((time.monotonic() - debut) * 1000),
        }

    def synchroniser(self, session: Session) -> dict:
        """Extrait les dossiers SharePoint vers Norix (création + pièces)."""
        debut = time.monotonic()
        donnees = self._manifeste()
        workflow = traitement_actif(session)
        if not workflow:
            raise ValueError("Aucun parcours actif dans Norix")

        dossiers_crees = 0
        dossiers_ignores = 0
        documents_importes = 0
        documents_ignores = 0
        polices_manquantes: list[str] = []

        for source in donnees["dossiers"]:
            pieces = [
                {
                    "type": doc["type"],
                    "chemin": doc["chemin"],
                    "source_connecteur": self.identifiant,
                    "source_nom": doc["nom_source"],
                    "recu_le": doc.get("recu_le")
                    or datetime.now(timezone.utc).isoformat(),
                    **(
                        {"montant": doc["montant"]}
                        if doc.get("montant") is not None
                        else {}
                    ),
                }
                for doc in source.get("documents", [])
            ]

            dossier = session.exec(
                select(Dossier).where(Dossier.ref == source["ref"])
            ).first()

            if not dossier:
                police_numero = (source.get("police_numero") or "").strip()
                police = None
                if police_numero:
                    police = session.exec(
                        select(Police).where(Police.numero == police_numero)
                    ).first()
                if not police:
                    # Fallback : première police disponible (démo)
                    police = session.exec(select(Police)).first()
                    if police_numero:
                        polices_manquantes.append(f"{source['ref']}:{police_numero}")
                if not police:
                    raise ValueError(
                        f"Aucune police Norix pour rattacher le dossier {source['ref']}"
                    )
                dossier = Dossier(
                    ref=source["ref"],
                    police_id=police.id,
                    workflow_id=workflow.id,
                    declaration_texte=source.get("declaration")
                    or f"Dossier extrait depuis SharePoint ({source['ref']}).",
                    etat="recu",
                    etape_courante=0,
                    pieces=pieces,
                    montant_estime=next(
                        (p.get("montant") for p in pieces if p.get("montant") is not None),
                        None,
                    ),
                )
                session.add(dossier)
                dossiers_crees += 1
                documents_importes += len(pieces)
                continue

            dossiers_ignores += 1
            # Dossier déjà dans Norix : rattacher seulement les nouvelles pièces
            pieces_actuelles = list(dossier.pieces or [])
            ajoutes = 0
            for piece in pieces:
                deja = any(
                    p.get("source_nom") == piece["source_nom"]
                    and p.get("source_connecteur") == self.identifiant
                    for p in pieces_actuelles
                )
                if deja:
                    documents_ignores += 1
                    continue
                pieces_actuelles.append(piece)
                ajoutes += 1
            if ajoutes:
                dossier.pieces = pieces_actuelles
                if dossier.montant_estime is None:
                    dossier.montant_estime = next(
                        (
                            p.get("montant")
                            for p in pieces_actuelles
                            if p.get("montant") is not None
                        ),
                        None,
                    )
                session.add(dossier)
                documents_importes += ajoutes
            else:
                documents_ignores += max(0, len(pieces) - ajoutes)

        resultat = {
            "statut": "succes",
            "source": donnees["source"],
            "dossiers_crees": dossiers_crees,
            "dossiers_ignores": dossiers_ignores,
            "documents_importes": documents_importes,
            "documents_ignores": documents_ignores,
            "polices_manquantes": sorted(set(polices_manquantes)),
            "duree_ms": int((time.monotonic() - debut) * 1000),
            "horodatage": datetime.now(timezone.utc).isoformat(),
        }
        if dossiers_crees or documents_importes:
            tracer(
                session,
                acteur="systeme:connecteur_sharepoint",
                acteur_type="agent",
                type="extraction_dossiers_sharepoint",
                objet=f"integration:{self.identifiant}",
                apres=resultat,
                motif="Extraction de dossiers depuis la bibliothèque SharePoint Sinistres",
            )
        session.commit()
        return resultat


def lister_bibliotheque() -> dict:
    connecteur = ConnecteurDocumentsLocal()
    if not MANIFESTE.exists():
        return {
            "source": "SharePoint Sinistres",
            "tenant": "Horizon Assurances",
            "bibliotheque": "Sinistres Auto / 2026",
            "dossiers": [],
            "retours": [],
        }
    return connecteur._manifeste()


def lister_documents() -> dict:
    """Compat API : aplatit les documents pour l'UI existante."""
    donnees = lister_bibliotheque()
    documents = []
    for dossier in donnees.get("dossiers", []):
        for doc in dossier.get("documents", []):
            documents.append(
                {
                    "dossier_ref": dossier["ref"],
                    "type": doc["type"],
                    "chemin": doc["chemin"],
                    "nom_source": doc["nom_source"],
                    "statut_sharepoint": dossier.get("statut_sharepoint", "a_traiter"),
                    **({"montant": doc["montant"]} if doc.get("montant") is not None else {}),
                    **({"recu_le": doc["recu_le"]} if doc.get("recu_le") else {}),
                }
            )
    return {
        "source": donnees["source"],
        "tenant": donnees.get("tenant"),
        "bibliotheque": donnees.get("bibliotheque"),
        "dossiers": donnees.get("dossiers", []),
        "retours": donnees.get("retours", []),
        "documents": documents,
    }


def ajouter_document(corps: dict) -> dict:
    """Ajoute une pièce dans un dossier SharePoint (crée le dossier si besoin)."""
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

    connecteur = ConnecteurDocumentsLocal()
    donnees = connecteur._manifeste() if MANIFESTE.exists() else {
        "source": "SharePoint Sinistres",
        "tenant": "Horizon Assurances",
        "bibliotheque": "Sinistres Auto / 2026",
        "dossiers": [],
        "retours": [],
    }

    document = {
        "type": type_piece,
        "chemin": chemin,
        "nom_source": nom_source,
        "recu_le": datetime.now(timezone.utc).isoformat(),
    }
    if corps.get("montant") not in (None, ""):
        document["montant"] = float(corps["montant"])

    cible = next((d for d in donnees["dossiers"] if d["ref"] == dossier_ref), None)
    if not cible:
        cible = {
            "ref": dossier_ref,
            "police_numero": (corps.get("police_numero") or "").strip(),
            "assure": corps.get("assure") or "Assuré SharePoint",
            "declaration": corps.get("declaration")
            or f"Dossier déposé dans SharePoint ({dossier_ref}).",
            "type_sinistre": corps.get("type_sinistre") or "collision",
            "statut_sharepoint": "a_traiter",
            "documents": [],
        }
        donnees["dossiers"].append(cible)
    cible["documents"] = [*cible.get("documents", []), document]
    connecteur._ecrire(donnees)
    return {
        "dossier_ref": dossier_ref,
        "type": type_piece,
        "chemin": chemin,
        "nom_source": nom_source,
        **({"montant": document["montant"]} if "montant" in document else {}),
    }


def deposer_retour(
    session: Session,
    dossier_id: int,
    validateur: str = "superviseur",
    *,
    commit: bool = True,
) -> dict:
    """Redépose un dossier traité (courrier / synthèse) dans SharePoint."""
    dossier = session.get(Dossier, dossier_id)
    if not dossier:
        raise ValueError("Dossier introuvable")
    if dossier.etat not in ETATS_TRAITES and not dossier.montant_valide:
        raise ValueError(
            "Le dossier doit être réglé, refusé ou clôturé (ou avoir un montant validé) "
            "avant dépôt dans SharePoint"
        )

    connecteur = ConnecteurDocumentsLocal()
    donnees = connecteur._manifeste()

    # Marquer le dossier source comme traité s'il existe
    for source in donnees["dossiers"]:
        if source["ref"] == dossier.ref:
            source["statut_sharepoint"] = "traite"
            break

    deja = next(
        (r for r in donnees["retours"] if r.get("dossier_ref") == dossier.ref),
        None,
    )
    if deja:
        return {"statut": "ignore", "retour": deja, "motif": "déjà déposé"}

    courrier = dossier.courrier or {}
    retour = {
        "dossier_ref": dossier.ref,
        "depose_le": datetime.now(timezone.utc).isoformat(),
        "depose_par": validateur,
        "automatique": True,
        "etat_norix": dossier.etat,
        "montant_valide": dossier.montant_valide,
        "objet": courrier.get("objet") or f"Décision sinistre {dossier.ref}",
        "corps": courrier.get("corps")
        or (
            f"Dossier {dossier.ref} traité dans Norix. "
            f"État : {dossier.etat}. "
            f"Montant validé : {dossier.montant_valide} TND."
            if dossier.montant_valide is not None
            else f"Dossier {dossier.ref} traité dans Norix (état : {dossier.etat})."
        ),
        "bibliotheque_cible": f"{donnees['bibliotheque']} / Traités / {dossier.ref}",
    }
    donnees["retours"] = [*donnees.get("retours", []), retour]
    connecteur._ecrire(donnees)

    tracer(
        session,
        acteur=f"humain:{validateur}" if validateur != "systeme" else "systeme:connecteur_sharepoint",
        acteur_type="humain" if validateur != "systeme" else "agent",
        type="depot_retour_sharepoint",
        objet=f"dossier:{dossier.ref}",
        apres=retour,
        motif="Dossier traité redéposé automatiquement dans SharePoint Sinistres",
    )
    if commit:
        session.commit()
    return {"statut": "succes", "retour": retour}
