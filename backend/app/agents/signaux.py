"""Signaux de cohérence déterministes — CODE PUR, aucun appel LLM.

Ces contrôles alimentent la porte humaine (agents/hitl.py) : ils signalent
une incohérence à vérifier, ils ne refusent et ne chiffrent jamais rien
eux-mêmes (principe M1.6 — voir CLAUDE.md §5).
"""
from datetime import timedelta
from pathlib import Path

from sqlmodel import Session, select

from .. import llm
from ..models import Dossier, Police

# Bibliothèque de démonstration partagée entre dossiers fictifs (seed, samples.py) :
# plusieurs dossiers du jeu de données pointent volontairement vers le même fichier
# (voir docs/inbox/sharepoint-manifest.json). Ce n'est jamais une pièce réelle d'un
# assuré : on l'exclut du contrôle de doublon pour ne pas signaler la démo elle-même.
PREFIXE_FIXTURES_DEMO = "docs/samples/"

# Hamming distance max sur un hash perceptuel 64 bits (aHash) pour parler de doublon —
# assez permissif pour absorber une recompression/redimension du même cliché.
SEUIL_DISTANCE_DOUBLON = 6

# Plafond indicatif (DT) au-delà duquel un montant devient disproportionné pour la
# classe de gravité retenue — barème volontairement large (faux positifs coûteux
# pour la confiance des gestionnaires), à confirmer avec l'encadrant métier.
PLAFOND_PLAUSIBLE_PAR_GRAVITE = {"leger": 3000.0, "moyen": 8000.0, "lourd": 30000.0}

# Fenêtre et seuil pour la fréquence de sinistres sur une même police.
FENETRE_FREQUENCE_JOURS = 180
SEUIL_NB_SINISTRES_FREQUENTS = 3

# Nombre minimal de dossiers d'assurés DIFFÉRENTS partageant le même émetteur de
# facture/devis avant de considérer que c'est un signal (pas juste un garage populaire).
SEUIL_DOSSIERS_EMETTEUR_PARTAGE = 2


def _normaliser_plaque(valeur: str) -> str:
    return "".join(caractere for caractere in valeur.upper() if caractere.isalnum())


def _chemin_fixture(chemin: str) -> bool:
    return chemin.replace("\\", "/").startswith(PREFIXE_FIXTURES_DEMO)


def verifier_plaque(dossier: Dossier, police: Police) -> dict | None:
    """Compare la plaque du contrat aux immatriculations lues sur les pièces jointes.

    Retourne None tant qu'aucune plaque n'a encore été extraite (rien à comparer) —
    ce n'est pas une absence de signal, juste un contrôle pas encore applicable.
    """
    plaque_contrat = (police.vehicule or {}).get("immatriculation")
    if not plaque_contrat:
        return None
    plaques_extraites = {
        plaque
        for piece in dossier.pieces
        for plaque in (piece.get("extraction") or {}).get("immatriculations", [])
        if plaque
    }
    if not plaques_extraites:
        return None

    reference = _normaliser_plaque(plaque_contrat)
    if any(_normaliser_plaque(p) == reference for p in plaques_extraites):
        return {
            "type": "plaque",
            "source": "deterministe",
            "statut": "coherent",
            "gravite": "info",
            "motif": f"Immatriculation {plaque_contrat} retrouvée sur les pièces jointes.",
        }
    return {
        "type": "plaque",
        "source": "deterministe",
        "statut": "incoherent",
        "gravite": "critique",
        "motif": (
            f"Le contrat mentionne {plaque_contrat}, mais les pièces jointes indiquent "
            f"{', '.join(sorted(plaques_extraites))} — véhicule potentiellement différent "
            "de celui assuré."
        ),
    }


def _hash_image(chemin: Path) -> int | None:
    """Hash perceptuel simple (aHash 8x8, niveaux de gris) — sans dépendance ajoutée."""
    try:
        from PIL import Image
    except ImportError:
        return None
    if not chemin.exists():
        return None
    try:
        image = Image.open(chemin).convert("L").resize((8, 8))
        pixels = list(image.getdata())
    except Exception:
        return None
    moyenne = sum(pixels) / len(pixels)
    bits = 0
    for pixel in pixels:
        bits = (bits << 1) | (1 if pixel >= moyenne else 0)
    return bits


def _distance_hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def detecter_doublons(session: Session, dossier: Dossier) -> list[dict]:
    """Repère une pièce déjà utilisée sur un AUTRE dossier, d'une AUTRE police.

    La réutilisation d'une même photo par le même assuré (ex. renvoi d'une pièce
    déjà transmise) n'est pas un signal ; celle vers un assuré/véhicule différent
    est un classique de la fraude documentaire (photo recyclée d'un sinistre
    antérieur ou trouvée ailleurs).
    """
    pieces_a_verifier = [
        p for p in dossier.pieces
        if p.get("chemin") and not _chemin_fixture(p["chemin"])
    ]
    if not pieces_a_verifier:
        return []

    autres_dossiers = session.exec(
        select(Dossier).where(Dossier.id != dossier.id)
    ).all()
    index: list[tuple[str, int]] = []
    for autre in autres_dossiers:
        if autre.police_id == dossier.police_id:
            continue
        for piece in autre.pieces:
            chemin = piece.get("chemin", "")
            if not chemin or _chemin_fixture(chemin):
                continue
            h = _hash_image(llm.RACINE / chemin)
            if h is not None:
                index.append((autre.ref, h))

    signaux: list[dict] = []
    for piece in pieces_a_verifier:
        h = _hash_image(llm.RACINE / piece["chemin"])
        if h is None:
            continue
        correspondance = next(
            (autre_ref for autre_ref, autre_hash in index if _distance_hamming(h, autre_hash) <= SEUIL_DISTANCE_DOUBLON),
            None,
        )
        if correspondance:
            signaux.append({
                "type": "doublon_photo",
                "source": "deterministe",
                "statut": "incoherent",
                "gravite": "critique",
                "motif": (
                    f"La pièce « {piece['chemin']} » correspond à une image déjà utilisée "
                    f"sur le dossier {correspondance} (assuré différent)."
                ),
            })
    return signaux


def _normaliser_emetteur(valeur: str) -> str:
    """Insensible à la casse, aux espaces et aux accents (variance d'OCR entre pièces)."""
    import unicodedata

    sans_accents = "".join(
        c for c in unicodedata.normalize("NFKD", valeur) if not unicodedata.combining(c)
    )
    return " ".join(sans_accents.lower().split())


def detecter_emetteur_partage(session: Session, dossier: Dossier) -> list[dict]:
    """Même émetteur de facture/devis que sur des dossiers d'assurés DIFFÉRENTS.

    Signal de collusion possible (garage complice), mais aussi vrai pour un garage
    simplement populaire — le motif reste prudent, jamais accusatoire.
    """
    pieces_chiffrees = [
        p for p in dossier.pieces
        if p.get("type") in ("facture", "devis")
        and p.get("chemin") and not _chemin_fixture(p["chemin"])
        and (p.get("extraction") or {}).get("emetteur")
    ]
    if not pieces_chiffrees:
        return []

    autres_dossiers = session.exec(
        select(Dossier).where(Dossier.id != dossier.id)
    ).all()
    refs_par_emetteur: dict[str, set[str]] = {}
    for autre in autres_dossiers:
        if autre.police_id == dossier.police_id:
            continue
        for piece in autre.pieces:
            if piece.get("type") not in ("facture", "devis"):
                continue
            if not piece.get("chemin") or _chemin_fixture(piece["chemin"]):
                continue
            emetteur = (piece.get("extraction") or {}).get("emetteur")
            if emetteur:
                refs_par_emetteur.setdefault(_normaliser_emetteur(emetteur), set()).add(autre.ref)

    signaux: list[dict] = []
    deja_signales: set[str] = set()
    for piece in pieces_chiffrees:
        emetteur = piece["extraction"]["emetteur"]
        cle = _normaliser_emetteur(emetteur)
        if cle in deja_signales:
            continue
        autres_refs = refs_par_emetteur.get(cle, set())
        if len(autres_refs) >= SEUIL_DOSSIERS_EMETTEUR_PARTAGE:
            deja_signales.add(cle)
            signaux.append({
                "type": "emetteur_partage",
                "source": "deterministe",
                "statut": "incoherent",
                "gravite": "attention",
                "motif": (
                    f"L'émetteur « {emetteur} » apparaît aussi sur {len(autres_refs)} autre(s) "
                    f"dossier(s) d'assurés différents ({', '.join(sorted(autres_refs)[:3])}) "
                    "— à vérifier (collusion possible, ou simplement un garage courant)."
                ),
            })
    return signaux


def verifier_montant_vs_gravite(dossier: Dossier) -> dict | None:
    """Montant chiffré très supérieur au plafond plausible pour la gravité retenue.

    Barème indicatif volontairement large : c'est un signal à vérifier par le
    gestionnaire, pas une preuve — un pare-brise avec calibrage ADAS peut coûter
    cher pour une gravité 'légère', par exemple.
    """
    if dossier.montant_estime is None or not dossier.gravite:
        return None
    plafond = PLAFOND_PLAUSIBLE_PAR_GRAVITE.get(dossier.gravite)
    if plafond is None:
        return None
    if dossier.montant_estime <= plafond:
        return {
            "type": "montant_vs_gravite",
            "source": "deterministe",
            "statut": "coherent",
            "gravite": "info",
            "motif": f"Montant de {dossier.montant_estime:.0f} DT cohérent avec une gravité '{dossier.gravite}'.",
        }
    return {
        "type": "montant_vs_gravite",
        "source": "deterministe",
        "statut": "incoherent",
        "gravite": "attention",
        "motif": (
            f"Montant estimé de {dossier.montant_estime:.0f} DT anormalement élevé pour une "
            f"gravité classée '{dossier.gravite}' (plafond indicatif : {plafond:.0f} DT) — "
            "à vérifier avant validation."
        ),
    }


def detecter_frequence_anormale(session: Session, dossier: Dossier) -> dict | None:
    """Plusieurs sinistres sur la même police dans une fenêtre de temps courte."""
    fenetre = dossier.cree_le - timedelta(days=FENETRE_FREQUENCE_JOURS)
    autres = session.exec(
        select(Dossier).where(
            Dossier.police_id == dossier.police_id,
            Dossier.id != dossier.id,
            Dossier.cree_le >= fenetre,
        )
    ).all()
    total = len(autres) + 1
    if total < SEUIL_NB_SINISTRES_FREQUENTS:
        return None
    return {
        "type": "frequence_sinistres",
        "source": "deterministe",
        "statut": "incoherent",
        "gravite": "attention",
        "motif": (
            f"{total} sinistres déclarés sur cette police en moins de "
            f"{FENETRE_FREQUENCE_JOURS} jours ({', '.join(sorted(a.ref for a in autres))}) "
            "— fréquence à examiner."
        ),
    }


def calculer(session: Session, dossier: Dossier, police: Police) -> list[dict]:
    """Point d'entrée unique : agrège tous les contrôles déterministes disponibles."""
    signaux: list[dict] = []
    plaque = verifier_plaque(dossier, police)
    if plaque:
        signaux.append(plaque)
    signaux.extend(detecter_doublons(session, dossier))
    signaux.extend(detecter_emetteur_partage(session, dossier))
    montant_gravite = verifier_montant_vs_gravite(dossier)
    if montant_gravite:
        signaux.append(montant_gravite)
    frequence = detecter_frequence_anormale(session, dossier)
    if frequence:
        signaux.append(frequence)
    return signaux
