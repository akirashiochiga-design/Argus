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


def _croquis_degats(titre: str, zones: list[tuple], annotations: list[str],
                    chemin: Path, fissure: bool = False) -> None:
    """Croquis d'expertise : vue de dessus du véhicule, zones endommagées hachurées.

    zones : liste de polygones [(x,y), ...] à hachurer en rouge sombre.
    """
    img = Image.new("RGB", (900, 1100), "#fdfcf8")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 900, 90], fill="#17150F")
    d.text((40, 26), titre, font=_police(28, True), fill="#F4F1EA")

    # Carrosserie vue de dessus (avant du véhicule en haut)
    encre = "#17150F"
    cx, haut, larg, longu = 450, 190, 300, 680
    d.rounded_rectangle([cx - larg // 2, haut, cx + larg // 2, haut + longu],
                        radius=90, outline=encre, width=5)
    # Roues
    for dx in (-1, 1):
        for dy in (150, 520):
            x = cx + dx * (larg // 2)
            d.rounded_rectangle([x - 14, haut + dy, x + 14, haut + dy + 110],
                                radius=12, fill=encre)
    # Pare-brise et lunette
    d.line([cx - 105, haut + 205, cx + 105, haut + 205], fill=encre, width=4)
    d.line([cx - 118, haut + 275, cx - 105, haut + 205], fill=encre, width=4)
    d.line([cx + 118, haut + 275, cx + 105, haut + 205], fill=encre, width=4)
    d.line([cx - 100, haut + 500, cx + 100, haut + 500], fill=encre, width=4)
    # Capot
    d.line([cx - 110, haut + 90, cx + 110, haut + 90], fill=encre, width=3)

    # Zones endommagées : hachures rouges
    rouge = "#B3402A"
    for poly in zones:
        d.polygon(poly, outline=rouge, width=4)
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        masque = Image.new("L", img.size, 0)
        ImageDraw.Draw(masque).polygon(poly, fill=255)
        hachures = Image.new("RGB", img.size, "#fdfcf8")
        dh = ImageDraw.Draw(hachures)
        for off in range(-(y1 - y0), x1 - x0 + (y1 - y0), 14):
            dh.line([x0 + off, y1, x0 + off + (y1 - y0), y0], fill=rouge, width=3)
        img.paste(hachures, (0, 0), masque)
        d.polygon(poly, outline=rouge, width=4)

    if fissure:  # fissure de pare-brise : ligne brisée dans la zone vitrée
        pts = [(cx - 80, haut + 250), (cx - 30, haut + 232), (cx + 5, haut + 248),
               (cx + 48, haut + 228), (cx + 88, haut + 240)]
        d.line(pts, fill=rouge, width=5)
        for p in pts[1:4]:
            d.line([p, (p[0] + 12, p[1] + 16)], fill=rouge, width=3)

    # Légende
    y = haut + longu + 50
    d.line([40, y - 18, 860, y - 18], fill="#d8d2c4", width=2)
    d.rectangle([40, y, 70, y + 20], outline=rouge, width=3)
    d.line([44, y + 18, 62, y + 2], fill=rouge, width=3)
    d.text((80, y), "zone endommagée constatée", font=_police(19), fill="#333333")
    y += 40
    for a in annotations:
        d.text((40, y), f"• {a}", font=_police(19), fill="#333333")
        y += 30
    d.text((40, 1050), "Croquis d'expertise établi sur constatations — démo (photos réelles à substituer)",
           font=_police(15), fill="#999999")
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

    # --- Croquis d'expertise (substituts des photos de dégâts, à remplacer si possible) ---
    # SIN-2026-001 : choc avant droit (pare-chocs + phare, puis aile)
    _croquis_degats(
        "SIN-2026-001 — dégâts avant droit (1/2)",
        [[(566, 196), (600, 214), (600, 268), (566, 262)]],
        ["Pare-chocs avant droit : enfoncé", "Optique avant droit : brisé",
         "Choc latéral, véhicule sortant d'un stationnement"],
        DOSSIER / "degats-1.jpg",
    )
    _croquis_degats(
        "SIN-2026-001 — dégâts avant droit (2/2)",
        [[(586, 300), (600, 300), (600, 380), (586, 380)]],
        ["Aile avant droite : tôle enfoncée", "Peinture à reprendre (aile + pare-chocs)",
         "Cohérent avec le constat amiable"],
        DOSSIER / "degats-2.jpg",
    )
    # SIN-2026-002 : choc frontal (capot + pare-chocs), gravité plus marquée
    _croquis_degats(
        "SIN-2026-002 — choc frontal",
        [[(330, 195), (570, 195), (560, 250), (340, 250)]],
        ["Capot : plié", "Pare-chocs avant : enfoncé sur toute la largeur",
         "Pas de tiers identifié, pas de constat"],
        DOSSIER / "degats-3.jpg",
    )
    # SIN-2026-003 : fissure de pare-brise
    _croquis_degats(
        "SIN-2026-003 — bris de glace",
        [],
        ["Fissure pare-brise côté conducteur (~30 cm)", "Impact d'un gravier projeté",
         "Remplacement préconisé"],
        DOSSIER / "parebrise.jpg",
        fissure=True,
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
    print("OK — 4 croquis de dégâts générés (substituts, à remplacer par de vraies photos si possible)")


if __name__ == "__main__":
    generer()
