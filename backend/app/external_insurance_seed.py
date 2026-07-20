"""Génère un SI assurance externe réaliste dans une seconde base SQLite."""
import sqlite3
from pathlib import Path


EXTERNAL_DB_PATH = Path(__file__).resolve().parent.parent / "insurance_core.db"


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS metadata (
    cle TEXT PRIMARY KEY,
    valeur TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assures (
    id INTEGER PRIMARY KEY,
    nom_complet TEXT NOT NULL,
    cin TEXT NOT NULL UNIQUE,
    telephone TEXT,
    ville TEXT
);

CREATE TABLE IF NOT EXISTS vehicules (
    id INTEGER PRIMARY KEY,
    assure_id INTEGER NOT NULL REFERENCES assures(id),
    marque TEXT NOT NULL,
    modele TEXT NOT NULL,
    immatriculation TEXT NOT NULL UNIQUE,
    annee INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS polices (
    id INTEGER PRIMARY KEY,
    numero TEXT NOT NULL UNIQUE,
    assure_id INTEGER NOT NULL REFERENCES assures(id),
    vehicule_id INTEGER NOT NULL REFERENCES vehicules(id),
    formule TEXT NOT NULL CHECK (formule IN ('tiers', 'tous_risques')),
    prime_payee INTEGER NOT NULL DEFAULT 1,
    date_effet TEXT NOT NULL,
    date_echeance TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS garanties (
    id INTEGER PRIMARY KEY,
    police_id INTEGER NOT NULL REFERENCES polices(id),
    code TEXT NOT NULL,
    plafond REAL NOT NULL,
    franchise REAL NOT NULL DEFAULT 0,
    UNIQUE(police_id, code)
);

CREATE TABLE IF NOT EXISTS sinistres (
    id INTEGER PRIMARY KEY,
    reference TEXT NOT NULL UNIQUE,
    police_id INTEGER NOT NULL REFERENCES polices(id),
    date_sinistre TEXT NOT NULL,
    declaration TEXT NOT NULL,
    type_sinistre TEXT NOT NULL,
    statut_source TEXT NOT NULL DEFAULT 'declare',
    montant_estime_source REAL
);

CREATE TABLE IF NOT EXISTS pieces (
    id INTEGER PRIMARY KEY,
    sinistre_id INTEGER NOT NULL REFERENCES sinistres(id),
    type_piece TEXT NOT NULL,
    chemin TEXT NOT NULL,
    montant_document REAL
);
"""


def ensure_external_db() -> Path:
    """Crée et peuple la base externe sans écraser les données existantes."""
    EXTERNAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(EXTERNAL_DB_PATH) as connexion:
        connexion.executescript(SCHEMA)
        connexion.executemany(
            "INSERT OR REPLACE INTO metadata(cle, valeur) VALUES (?, ?)",
            [
                ("schema_version", "1"),
                ("systeme_source", "CoreSinistre"),
                ("organisation", "Horizon Assurances"),
            ],
        )
        connexion.executemany(
            """INSERT OR IGNORE INTO assures
               (id, nom_complet, cin, telephone, ville) VALUES (?, ?, ?, ?, ?)""",
            [
                (102, "Inès Trabelsi", "08963214", "+216 55 208 419", "Sfax"),
                (103, "Youssef Gharbi", "06745198", "+216 98 330 512", "Sousse"),
                (104, "Amira Jlassi", "09521476", "+216 29 415 008", "Nabeul"),
            ],
        )
        connexion.executemany(
            """INSERT OR IGNORE INTO vehicules
               (id, assure_id, marque, modele, immatriculation, annee)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (202, 102, "Renault", "Clio 5", "224 TU 1693", 2021),
                (203, 103, "Volkswagen", "Golf 8", "238 TU 5501", 2024),
                (204, 104, "Hyundai", "i20", "219 TU 7340", 2020),
            ],
        )
        connexion.executemany(
            """INSERT OR IGNORE INTO polices
               (id, numero, assure_id, vehicule_id, formule, prime_payee,
                date_effet, date_echeance, statut)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (302, "EXT-AUTO-1002", 102, 202, "tiers", 1, "2026-02-10", "2027-02-09", "active"),
                (303, "EXT-AUTO-1003", 103, 203, "tous_risques", 1, "2025-11-15", "2026-11-14", "active"),
                (304, "EXT-AUTO-1004", 104, 204, "tous_risques", 0, "2026-03-01", "2027-02-28", "suspendue"),
            ],
        )
        connexion.executemany(
            """INSERT OR IGNORE INTO garanties
               (police_id, code, plafond, franchise) VALUES (?, ?, ?, ?)""",
            [
                (302, "rc", 100000, 0),
                (303, "collision", 40000, 250),
                (303, "bris_glace", 3500, 80),
                (303, "rc", 100000, 0),
                (304, "collision", 25000, 350),
                (304, "bris_glace", 2000, 120),
                (304, "rc", 100000, 0),
            ],
        )
        connexion.executemany(
            """INSERT OR IGNORE INTO sinistres
               (id, reference, police_id, date_sinistre, declaration,
                type_sinistre, statut_source, montant_estime_source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    402,
                    "EXT-SIN-2026-1002",
                    302,
                    "2026-07-18",
                    "Choc arrière lors d'un stationnement. Le hayon et le feu arrière sont touchés.",
                    "collision",
                    "declare",
                    1800,
                ),
                (
                    403,
                    "EXT-SIN-2026-1003",
                    303,
                    "2026-07-18",
                    "Projection de gravier sur autoroute avec fissure importante du pare-brise.",
                    "bris_glace",
                    "declare",
                    850,
                ),
            ],
        )
        connexion.executemany(
            """INSERT OR IGNORE INTO pieces
               (id, sinistre_id, type_piece, chemin, montant_document)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (504, 402, "devis", "docs/samples/devis.jpg", 1800),
                (505, 402, "photo_degats", "docs/samples/degats-2.jpg", None),
                (506, 403, "devis", "docs/samples/devis-parebrise.jpg", 850),
                (507, 403, "photo_degats", "docs/samples/parebrise.jpg", None),
            ],
        )
        connexion.commit()
    return EXTERNAL_DB_PATH


if __name__ == "__main__":
    chemin = ensure_external_db()
    print(f"Base assurance externe prête : {chemin}")
