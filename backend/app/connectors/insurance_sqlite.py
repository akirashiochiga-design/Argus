"""Connecteur en lecture seule vers le SI assurance SQLite externe."""
import sqlite3
import time
from datetime import datetime, timezone

from sqlmodel import Session, select

from ..audit import tracer
from ..external_insurance_seed import EXTERNAL_DB_PATH, ensure_external_db
from ..models import Dossier, Police
from ..workflow_service import traitement_actif


TABLES_ATTENDUES = {
    "metadata",
    "assures",
    "vehicules",
    "polices",
    "garanties",
    "sinistres",
    "pieces",
}


class ConnexionAssuranceInvalide(Exception):
    """La base externe est absente ou son schéma n'est pas compatible."""


def _connexion() -> sqlite3.Connection:
    ensure_external_db()
    try:
        connexion = sqlite3.connect(
            f"{EXTERNAL_DB_PATH.resolve().as_uri()}?mode=ro",
            uri=True,
            timeout=5,
        )
        connexion.row_factory = sqlite3.Row
        connexion.execute("PRAGMA query_only = ON")
        return connexion
    except sqlite3.Error as e:
        raise ConnexionAssuranceInvalide(f"Connexion à la base assurance impossible : {e}") from e


def _tables(connexion: sqlite3.Connection) -> set[str]:
    return {
        ligne["name"]
        for ligne in connexion.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def tester_connexion() -> dict:
    """Ouvre réellement la base et vérifie les tables attendues."""
    debut = time.monotonic()
    with _connexion() as connexion:
        tables = _tables(connexion)
        manquantes = sorted(TABLES_ATTENDUES - tables)
        if manquantes:
            raise ConnexionAssuranceInvalide(
                f"Schéma incompatible, tables manquantes : {', '.join(manquantes)}"
            )
        metadata = {
            ligne["cle"]: ligne["valeur"]
            for ligne in connexion.execute("SELECT cle, valeur FROM metadata")
        }
        compteurs = {
            table: connexion.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("assures", "vehicules", "polices", "garanties", "sinistres", "pieces")
        }
    return {
        "statut": "connecte",
        "source": metadata.get("systeme_source", "Base assurance"),
        "organisation": metadata.get("organisation"),
        "fichier": EXTERNAL_DB_PATH.name,
        "schema_version": metadata.get("schema_version"),
        "tables": sorted(tables),
        "compteurs": compteurs,
        "latence_ms": int((time.monotonic() - debut) * 1000),
    }


def _nom_masque(nom: str) -> str:
    parties = nom.split()
    if len(parties) < 2:
        return nom
    return f"{parties[0]} " + " ".join(f"{partie[0]}." for partie in parties[1:])


def apercu() -> dict:
    """Retourne un aperçu limité et sans identifiant personnel sensible."""
    connexion_info = tester_connexion()
    with _connexion() as connexion:
        polices = [
            {
                "numero": ligne["numero"],
                "assure": _nom_masque(ligne["nom_complet"]),
                "formule": ligne["formule"],
                "vehicule": f"{ligne['marque']} {ligne['modele']}",
                "immatriculation": ligne["immatriculation"],
                "prime_payee": bool(ligne["prime_payee"]),
            }
            for ligne in connexion.execute(
                """SELECT p.numero, p.formule, p.prime_payee, a.nom_complet,
                          v.marque, v.modele, v.immatriculation
                   FROM polices p
                   JOIN assures a ON a.id = p.assure_id
                   JOIN vehicules v ON v.id = p.vehicule_id
                   ORDER BY p.numero
                   LIMIT 5"""
            )
        ]
        sinistres = [
            {
                "reference": ligne["reference"],
                "police_numero": ligne["numero"],
                "date_sinistre": ligne["date_sinistre"],
                "type_sinistre": ligne["type_sinistre"],
                "statut_source": ligne["statut_source"],
                "nombre_pieces": ligne["nombre_pieces"],
            }
            for ligne in connexion.execute(
                """SELECT s.reference, p.numero, s.date_sinistre, s.type_sinistre,
                          s.statut_source, COUNT(pc.id) AS nombre_pieces
                   FROM sinistres s
                   JOIN polices p ON p.id = s.police_id
                   LEFT JOIN pieces pc ON pc.sinistre_id = s.id
                   GROUP BY s.id
                   ORDER BY s.date_sinistre DESC, s.reference
                   LIMIT 5"""
            )
        ]
    return {**connexion_info, "apercu_polices": polices, "apercu_sinistres": sinistres}


def _polices_source(connexion: sqlite3.Connection) -> list[dict]:
    lignes = connexion.execute(
        """SELECT p.id, p.numero, p.formule, p.prime_payee, a.nom_complet,
                  v.marque, v.modele, v.immatriculation, v.annee,
                  g.code, g.plafond, g.franchise
           FROM polices p
           JOIN assures a ON a.id = p.assure_id
           JOIN vehicules v ON v.id = p.vehicule_id
           LEFT JOIN garanties g ON g.police_id = p.id
           ORDER BY p.numero, g.code"""
    )
    par_numero: dict[str, dict] = {}
    for ligne in lignes:
        police = par_numero.setdefault(
            ligne["numero"],
            {
                "id_source": ligne["id"],
                "numero": ligne["numero"],
                "assure_nom": ligne["nom_complet"],
                "formule": ligne["formule"],
                "prime_payee": bool(ligne["prime_payee"]),
                "vehicule": {
                    "marque": ligne["marque"],
                    "modele": ligne["modele"],
                    "immatriculation": ligne["immatriculation"],
                    "annee": ligne["annee"],
                },
                "garanties": {},
            },
        )
        if ligne["code"]:
            police["garanties"][ligne["code"]] = {
                "plafond": float(ligne["plafond"]),
                "franchise": float(ligne["franchise"]),
            }
    return list(par_numero.values())


def _pieces_source(connexion: sqlite3.Connection, sinistre_id: int) -> list[dict]:
    pieces = []
    for ligne in connexion.execute(
        """SELECT type_piece, chemin, montant_document
           FROM pieces WHERE sinistre_id = ? ORDER BY id""",
        (sinistre_id,),
    ):
        piece = {"type": ligne["type_piece"], "chemin": ligne["chemin"]}
        if ligne["montant_document"] is not None:
            piece["montant"] = float(ligne["montant_document"])
        if ligne["chemin"] == "docs/samples/degats-2.jpg":
            piece.update(
                {
                    "coherence_attendue": False,
                    "incoherente_declaration": True,
                    "motif_incoherence": (
                        "La déclaration concerne une Renault Clio blanche touchée à l'arrière, "
                        "alors que la photo montre une Toyota rouge endommagée à l'avant."
                    ),
                }
            )
        pieces.append(piece)
    return pieces


def synchroniser(session: Session) -> dict:
    """Importe ou met à jour les polices puis ajoute les nouveaux sinistres."""
    debut = time.monotonic()
    info = tester_connexion()
    workflow = traitement_actif(session)
    if not workflow:
        raise ConnexionAssuranceInvalide("Aucun parcours actif dans Argus")

    compteurs = {
        "polices_creees": 0,
        "polices_mises_a_jour": 0,
        "polices_inchangees": 0,
        "sinistres_crees": 0,
        "sinistres_ignores": 0,
    }
    with _connexion() as connexion:
        for source in _polices_source(connexion):
            police = session.exec(
                select(Police).where(Police.numero == source["numero"])
            ).first()
            valeurs = {
                "assure_nom": source["assure_nom"],
                "formule": source["formule"],
                "prime_payee": source["prime_payee"],
                "vehicule": source["vehicule"],
                "garanties": source["garanties"],
            }
            if not police:
                police = Police(numero=source["numero"], **valeurs)
                session.add(police)
                compteurs["polices_creees"] += 1
            elif any(getattr(police, cle) != valeur for cle, valeur in valeurs.items()):
                for cle, valeur in valeurs.items():
                    setattr(police, cle, valeur)
                session.add(police)
                compteurs["polices_mises_a_jour"] += 1
            else:
                compteurs["polices_inchangees"] += 1
        session.flush()

        polices_argus = {
            police.numero: police
            for police in session.exec(
                select(Police).where(
                    Police.numero.in_([source["numero"] for source in _polices_source(connexion)])
                )
            ).all()
        }
        sinistres_source = connexion.execute(
            """SELECT s.id, s.reference, s.declaration, p.numero AS police_numero
               FROM sinistres s
               JOIN polices p ON p.id = s.police_id
               ORDER BY s.reference"""
        )
        for source in sinistres_source:
            existe = session.exec(
                select(Dossier).where(Dossier.ref == source["reference"])
            ).first()
            if existe:
                pieces_source = _pieces_source(connexion, source["id"])
                if existe.etape_courante == 0 and existe.pieces != pieces_source:
                    existe.pieces = pieces_source
                    session.add(existe)
                compteurs["sinistres_ignores"] += 1
                continue
            police = polices_argus[source["police_numero"]]
            dossier = Dossier(
                ref=source["reference"],
                police_id=police.id,
                workflow_id=workflow.id,
                declaration_texte=source["declaration"],
                etat="recu",
                etape_courante=0,
                pieces=_pieces_source(connexion, source["id"]),
            )
            session.add(dossier)
            compteurs["sinistres_crees"] += 1

    resultat = {
        "statut": "succes",
        "source": info["source"],
        **compteurs,
        "duree_ms": int((time.monotonic() - debut) * 1000),
        "horodatage": datetime.now(timezone.utc).isoformat(),
    }
    tracer(
        session,
        acteur="systeme:connecteur_assurance",
        acteur_type="agent",
        type="synchronisation_donnees",
        objet="integration:insurance_core",
        apres=resultat,
        motif="Synchronisation manuelle depuis le SI assurance",
    )
    session.commit()
    return resultat


class ConnecteurAssuranceSQLite:
    """Adaptateur du SI de démonstration conforme au registre Argus."""

    identifiant = "insurance_core"
    nom = "AssurCore Auto"
    direction = "entrant"

    def tester(self) -> dict:
        return tester_connexion()

    def synchroniser(self, session: Session) -> dict:
        return synchroniser(session)
