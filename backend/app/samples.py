"""Génère les documents d'exemple de docs/samples/ (factures, devis, constat).

Usage : python -m app.samples
Images de documents réalistes (texte lisible) pour l'agent extraction vision.
Les PHOTOS DE DÉGÂTS ne sont pas générées : y déposer de vraies photos
(voir docs/samples/README.md) — en leur absence, l'agent gravité bascule
en estimation sur déclaration.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DOSSIER = Path(__file__).resolve().parent.parent.parent / "docs" / "samples"


def _police(taille: int, gras: bool = False) -> ImageFont.FreeTypeFont:
    nom = "arialbd.ttf" if gras else "arial.ttf"
    try:
        return ImageFont.truetype(nom, taille)
    except OSError:
        return ImageFont.load_default(taille)


def _document(titre: str, entete: list[str], lignes: list[tuple[str, str]],
              total: str, pied: str, chemin: Path) -> None:
    img = Image.new("RGB", (900, 1100), "#fdfcf8")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 900, 110], fill="#1e3a5f")
    d.text((40, 30), titre, font=_police(34, True), fill="white")

    y = 150
    for ligne in entete:
        d.text((40, y), ligne, font=_police(20), fill="#333333")
        y += 32

    y += 30
    d.rectangle([40, y, 860, y + 44], fill="#e8e4da")
    d.text((60, y + 10), "Désignation", font=_police(20, True), fill="#1e3a5f")
    d.text((640, y + 10), "Montant (DT)", font=_police(20, True), fill="#1e3a5f")
    y += 44
    for libelle, montant in lignes:
        d.line([40, y + 42, 860, y + 42], fill="#dddddd")
        d.text((60, y + 10), libelle, font=_police(20), fill="#222222")
        d.text((640, y + 10), montant, font=_police(20), fill="#222222")
        y += 44

    y += 26
    d.rectangle([480, y, 860, y + 54], fill="#1e3a5f")
    d.text((500, y + 12), "TOTAL TTC", font=_police(24, True), fill="white")
    d.text((640, y + 12), total, font=_police(24, True), fill="white")

    d.text((40, 1020), pied, font=_police(16), fill="#777777")
    img.save(chemin, quality=90)
    print(f"  {chemin.name}")


def generer() -> None:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    print("Génération des documents d'exemple :")

    # Dossier SIN-2026-001 — LA facture calibrée : total 2 300 DT
    _document(
        "GARAGE BEN ROMDHANE — FACTURE",
        ["Facture N° F-2026-0447          Date : 14/07/2026",
         "Client : Ahmed Ben Salah",
         "Véhicule : Volkswagen Golf 8 — 225 TU 4817",
         "Sinistre : choc avant droit"],
        [("Pare-chocs avant (pièce + pose)", "620,00"),
         ("Optique phare avant droit", "540,00"),
         ("Aile avant droite — tôlerie", "480,00"),
         ("Peinture (aile + pare-chocs)", "410,00"),
         ("Main d'œuvre carrosserie (5 h)", "250,00")],
        "2 300,00",
        "Garage Ben Romdhane — Route de l'Ariana, Tunis — MF 1234567/A/M/000",
        DOSSIER / "facture.jpg",
    )

    # Dossier SIN-2026-002 — devis 1 750 DT (sera refusé : formule tiers)
    _document(
        "CARROSSERIE EL MANAR — DEVIS",
        ["Devis N° D-2026-0912          Date : 16/07/2026",
         "Client : Fatma Trabelsi",
         "Véhicule : Peugeot 208 — 198 TU 2231",
         "Dégâts : capot et pare-chocs avant enfoncés"],
        [("Capot (pièce adaptable + pose)", "780,00"),
         ("Pare-chocs avant", "450,00"),
         ("Peinture capot + pare-chocs", "380,00"),
         ("Main d'œuvre (3 h)", "140,00")],
        "1 750,00",
        "Carrosserie El Manar — Av. de la Liberté, Tunis",
        DOSSIER / "devis.jpg",
    )

    # Dossier SIN-2026-003 — devis pare-brise 420 DT (sous le seuil)
    _document(
        "TUNISIE PARE-BRISE — DEVIS",
        ["Devis N° PB-2026-1188          Date : 18/07/2026",
         "Client : Nour Chaabane",
         "Véhicule : Hyundai i20 — 251 TU 3308",
         "Intervention : remplacement pare-brise"],
        [("Pare-brise feuilleté d'origine", "320,00"),
         ("Kit de collage + joint", "45,00"),
         ("Main d'œuvre et calibrage", "55,00")],
        "420,00",
        "Tunisie Pare-Brise — La Marsa — intervention à domicile",
        DOSSIER / "devis-parebrise.jpg",
    )

    # Constat simplifié (texte) pour SIN-2026-001
    _document(
        "CONSTAT AMIABLE D'ACCIDENT (extrait)",
        ["Date : 13/07/2026 à 19h30 — Lieu : Av. Habib Bourguiba, Ariana",
         "Véhicule A : VW Golf 8 — 225 TU 4817 — Ahmed Ben Salah",
         "Véhicule B : Renault Symbol — 190 TU 7752 — conducteur adverse",
         "Croquis : B sortait d'un parking, choc sur avant droit de A",
         "Case 8 cochée (B sortait d'un stationnement) — B reconnaît ses torts"],
        [("Dégâts véhicule A : pare-chocs avant droit", "—"),
         ("Dégâts véhicule A : optique droit, aile enfoncée", "—"),
         ("Signatures : A ✔   B ✔", "—")],
        "—",
        "Document reconstitué pour démo — remplacer par un vrai constat scanné si possible",
        DOSSIER / "constat.jpg",
    )
    print("OK — photos de dégâts à ajouter manuellement (degats-1.jpg, degats-2.jpg, degats-3.jpg, parebrise.jpg)")


if __name__ == "__main__":
    generer()
