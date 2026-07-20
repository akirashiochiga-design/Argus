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


def _connexion_ecriture() -> sqlite3.Connection:
    """Ouverture en écriture pour alimenter le SI source (parcours démo)."""
    ensure_external_db()
    try:
        connexion = sqlite3.connect(EXTERNAL_DB_PATH, timeout=5)
        connexion.row_factory = sqlite3.Row
        connexion.execute("PRAGMA foreign_keys = ON")
        return connexion
    except sqlite3.Error as e:
        raise ConnexionAssuranceInvalide(f"Écriture dans la base assurance impossible : {e}") from e


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
                """
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
                "declaration": ligne["declaration"],
            }
            for ligne in connexion.execute(
                """SELECT s.reference, p.numero, s.date_sinistre, s.type_sinistre,
                          s.statut_source, s.declaration, COUNT(pc.id) AS nombre_pieces
                   FROM sinistres s
                   JOIN polices p ON p.id = s.police_id
                   LEFT JOIN pieces pc ON pc.sinistre_id = s.id
                   GROUP BY s.id
                   ORDER BY s.date_sinistre DESC, s.reference
                """
            )
        ]
    return {**connexion_info, "apercu_polices": polices, "apercu_sinistres": sinistres}


def inventaire() -> dict:
    """Vue complète du SI source (pour le panneau CoreSinistre)."""
    return apercu()


def _prochain_numero(connexion: sqlite3.Connection, table: str, colonne: str, prefixe: str) -> str:
    lignes = connexion.execute(
        f"SELECT {colonne} AS valeur FROM {table} WHERE {colonne} LIKE ?",
        (f"{prefixe}%",),
    ).fetchall()
    max_n = 0
    for ligne in lignes:
        suffixe = str(ligne["valeur"])[len(prefixe):]
        if suffixe.isdigit():
            max_n = max(max_n, int(suffixe))
    return f"{prefixe}{max_n + 1:04d}"


def creer_police(donnees: dict) -> dict:
    """Ajoute un contrat dans CoreSinistre (pas encore dans Norix)."""
    nom = (donnees.get("assure_nom") or "").strip()
    marque = (donnees.get("marque") or "").strip()
    modele = (donnees.get("modele") or "").strip()
    immatriculation = (donnees.get("immatriculation") or "").strip().upper()
    formule = donnees.get("formule") or "tous_risques"
    if formule not in ("tiers", "tous_risques"):
        raise ValueError("Formule invalide")
    if not nom or not marque or not modele or not immatriculation:
        raise ValueError("Assuré, véhicule et immatriculation sont requis")

    with _connexion_ecriture() as connexion:
        if connexion.execute(
            "SELECT 1 FROM vehicules WHERE immatriculation = ?", (immatriculation,)
        ).fetchone():
            raise ValueError(f"Immatriculation déjà connue : {immatriculation}")

        numero = (donnees.get("numero") or "").strip() or _prochain_numero(
            connexion, "polices", "numero", "EXT-AUTO-"
        )
        if connexion.execute(
            "SELECT 1 FROM polices WHERE numero = ?", (numero,)
        ).fetchone():
            raise ValueError(f"Police déjà existante : {numero}")

        cur = connexion.execute(
            """INSERT INTO assures (nom_complet, cin, telephone, ville)
               VALUES (?, ?, ?, ?)""",
            (
                nom,
                donnees.get("cin") or f"CIN{int(time.time()) % 100000000:08d}",
                donnees.get("telephone") or "+216 20 000 000",
                donnees.get("ville") or "Tunis",
            ),
        )
        assure_id = cur.lastrowid
        cur = connexion.execute(
            """INSERT INTO vehicules
               (assure_id, marque, modele, immatriculation, annee)
               VALUES (?, ?, ?, ?, ?)""",
            (assure_id, marque, modele, immatriculation, int(donnees.get("annee") or 2023)),
        )
        vehicule_id = cur.lastrowid
        cur = connexion.execute(
            """INSERT INTO polices
               (numero, assure_id, vehicule_id, formule, prime_payee,
                date_effet, date_echeance, statut)
               VALUES (?, ?, ?, ?, 1, date('now'), date('now', '+1 year'), 'active')""",
            (numero, assure_id, vehicule_id, formule),
        )
        police_id = cur.lastrowid
        garanties = (
            [("rc", 100000, 0)]
            if formule == "tiers"
            else [
                ("collision", 45000, 300),
                ("bris_glace", 3000, 100),
                ("rc", 100000, 0),
            ]
        )
        connexion.executemany(
            """INSERT INTO garanties (police_id, code, plafond, franchise)
               VALUES (?, ?, ?, ?)""",
            [(police_id, code, plafond, franchise) for code, plafond, franchise in garanties],
        )
        connexion.commit()

    return {
        "numero": numero,
        "assure_nom": nom,
        "formule": formule,
        "vehicule": f"{marque} {modele}",
        "immatriculation": immatriculation,
    }


def creer_sinistre(donnees: dict) -> dict:
    """Ajoute un sinistre dans CoreSinistre, rattaché à une police source."""
    police_numero = (donnees.get("police_numero") or "").strip()
    declaration = (donnees.get("declaration") or "").strip()
    type_sinistre = (donnees.get("type_sinistre") or "collision").strip()
    if not police_numero or not declaration:
        raise ValueError("Police et déclaration sont requis")

    with _connexion_ecriture() as connexion:
        police = connexion.execute(
            "SELECT id, numero FROM polices WHERE numero = ?", (police_numero,)
        ).fetchone()
        if not police:
            raise ValueError(f"Police introuvable dans CoreSinistre : {police_numero}")

        reference = (donnees.get("reference") or "").strip() or _prochain_numero(
            connexion, "sinistres", "reference", "EXT-SIN-2026-"
        )
        if connexion.execute(
            "SELECT 1 FROM sinistres WHERE reference = ?", (reference,)
        ).fetchone():
            raise ValueError(f"Référence déjà existante : {reference}")

        montant = donnees.get("montant_estime")
        cur = connexion.execute(
            """INSERT INTO sinistres
               (reference, police_id, date_sinistre, declaration,
                type_sinistre, statut_source, montant_estime_source)
               VALUES (?, ?, date('now'), ?, ?, 'declare', ?)""",
            (
                reference,
                police["id"],
                declaration,
                type_sinistre,
                float(montant) if montant not in (None, "") else None,
            ),
        )
        sinistre_id = cur.lastrowid

        pieces = donnees.get("pieces")
        if pieces is None:
            pieces = [
                {"type": "constat", "chemin": "docs/samples/constat.jpg"},
                {"type": "photo_degats", "chemin": "docs/samples/degats-1.jpg"},
            ]
            if montant not in (None, ""):
                pieces.append(
                    {
                        "type": "devis",
                        "chemin": "docs/samples/devis.jpg",
                        "montant": float(montant),
                    }
                )
        for piece in pieces:
            connexion.execute(
                """INSERT INTO pieces
                   (sinistre_id, type_piece, chemin, montant_document)
                   VALUES (?, ?, ?, ?)""",
                (
                    sinistre_id,
                    piece["type"],
                    piece["chemin"],
                    piece.get("montant"),
                ),
            )
        connexion.commit()

    return {
        "reference": reference,
        "police_numero": police_numero,
        "type_sinistre": type_sinistre,
        "nombre_pieces": len(pieces),
    }


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
        raise ConnexionAssuranceInvalide("Aucun parcours actif dans Norix")

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

        polices_norix = {
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
            police = polices_norix[source["police_numero"]]
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
    """Adaptateur du SI core assurance conforme au registre Norix."""

    identifiant = "insurance_core"
    nom = "CoreSinistre"
    direction = "entrant"

    def tester(self) -> dict:
        return tester_connexion()

    def synchroniser(self, session: Session) -> dict:
        return synchroniser(session)
