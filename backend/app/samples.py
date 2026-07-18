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
    img = Image.new("RGB", (900, 1100), "#f8f7f3")
    d = ImageDraw.Draw(img)
    # Feuille scannée avec marges, en-tête garage et références comptables.
    d.rectangle([24, 18, 876, 1080], fill="white", outline="#d3d0c8", width=2)
    d.rectangle([48, 42, 132, 126], fill="#243b53")
    d.text((70, 62), "GB", font=_police(28, True), fill="white")
    d.text((154, 48), titre.split("—")[0].strip(), font=_police(25, True), fill="#172b4d")
    d.text((154, 82), "Carrosserie · peinture · mécanique", font=_police(16), fill="#5d6774")
    nature = titre.split("—")[-1].strip()
    d.text((690, 50), nature, font=_police(28, True), fill="#172b4d")
    d.text((690, 88), "ORIGINAL", font=_police(14, True), fill="#b3402a")
    d.line([48, 144, 852, 144], fill="#243b53", width=3)

    y = 174
    for i, ligne in enumerate(entete):
        if i == 0:
            d.rounded_rectangle([480, y - 10, 842, y + 34], radius=5, fill="#eef2f6")
            d.text((496, y), ligne, font=_police(16, True), fill="#243b53")
        else:
            d.text((58, y), ligne, font=_police(18), fill="#28323c")
        y += 34

    y += 18
    d.rectangle([48, y, 852, y + 46], fill="#243b53")
    d.text((62, y + 12), "DÉSIGNATION DES TRAVAUX", font=_police(17, True), fill="white")
    d.text((700, y + 12), "MONTANT DT", font=_police(17, True), fill="white")
    y += 46
    for libelle, montant in lignes:
        d.rectangle([48, y, 852, y + 48], outline="#d9dde2")
        d.text((62, y + 13), libelle, font=_police(17), fill="#202a35")
        d.text((720, y + 13), montant, font=_police(17), fill="#202a35")
        y += 48

    y += 22
    d.text((560, y), "Total HT", font=_police(17), fill="#5d6774")
    d.text((720, y), total, font=_police(17), fill="#5d6774")
    d.text((560, y + 34), "TVA", font=_police(17), fill="#5d6774")
    d.text((720, y + 34), "incluse", font=_police(17), fill="#5d6774")
    d.rectangle([540, y + 70, 852, y + 128], fill="#243b53")
    d.text((558, y + 86), "TOTAL TTC", font=_police(21, True), fill="white")
    d.text((712, y + 86), total, font=_police(21, True), fill="white")

    d.line([48, 976, 852, 976], fill="#d3d0c8", width=2)
    d.text((58, 994), pied, font=_police(14), fill="#68727d")
    d.text((58, 1022), "Règlement : virement ou chèque",
           font=_police(13), fill="#8b939c")
    img.save(chemin, quality=90)
    print(f"  {chemin.name}")


def _constat(chemin: Path) -> None:
    """Formulaire de constat amiable réaliste, structuré comme un imprimé assurance."""
    img = Image.new("RGB", (1100, 820), "#efede6")
    d = ImageDraw.Draw(img)
    d.rectangle([20, 16, 1080, 804], fill="#fffef9", outline="#9d9a91", width=2)
    d.rectangle([36, 30, 1064, 92], fill="#f2c94c")
    d.text((54, 44), "CONSTAT AMIABLE D'ACCIDENT AUTOMOBILE", font=_police(25, True), fill="#242424")
    d.text((838, 47), "Exemplaire assureur", font=_police(14, True), fill="#6b5700")

    champs = [
        ("1. Date", "13/07/2026 — 19h30"),
        ("2. Lieu", "Av. Habib Bourguiba, Ariana"),
        ("3. Blessés", "☐ oui   ☒ non"),
        ("4. Dégâts matériels autres", "☐ oui   ☒ non"),
    ]
    x = 44
    for titre, valeur in champs:
        d.rectangle([x, 110, x + 245, 174], outline="#77736c")
        d.text((x + 8, 118), titre, font=_police(13, True), fill="#55514b")
        d.text((x + 8, 144), valeur, font=_police(14), fill="#171717")
        x += 253

    d.rectangle([44, 190, 530, 630], outline="#3978a8", width=3)
    d.rectangle([570, 190, 1056, 630], outline="#d04b3e", width=3)
    d.rectangle([44, 190, 530, 232], fill="#dbeef8")
    d.rectangle([570, 190, 1056, 232], fill="#f8dfdc")
    d.text((60, 201), "VÉHICULE A — ASSURÉ", font=_police(18, True), fill="#1e557d")
    d.text((586, 201), "VÉHICULE B — TIERS", font=_police(18, True), fill="#97352d")

    a = [
        "Nom : Ahmed Ben Salah",
        "Assureur : Argus Assurances",
        "Police : PA-2024-1183",
        "Véhicule : Volkswagen Golf 8",
        "Immatriculation : 225 TU 4817",
        "Point de choc : avant droit",
        "Dégâts : pare-chocs, optique, aile",
    ]
    b = [
        "Nom : Mohamed R. (conducteur)",
        "Assureur : Assurances du Centre",
        "Police : AC-88421",
        "Véhicule : Renault Symbol",
        "Immatriculation : 190 TU 7752",
        "☒ Sortait d'un stationnement",
        "Observations : torts reconnus",
    ]
    for col_x, lignes in ((60, a), (586, b)):
        y = 250
        for ligne in lignes:
            d.text((col_x, y), ligne, font=_police(15), fill="#262626")
            d.line([col_x, y + 23, col_x + 440, y + 23], fill="#ddd9d0")
            y += 43

    d.rectangle([44, 648, 680, 770], outline="#77736c")
    d.text((56, 658), "Croquis de l'accident", font=_police(14, True), fill="#4d4943")
    d.line([260, 712, 590, 712], fill="#77736c", width=5)
    d.rectangle([170, 688, 245, 738], outline="#3978a8", width=3)
    d.rectangle([600, 676, 650, 746], outline="#d04b3e", width=3)
    d.line([595, 711, 542, 711], fill="#d04b3e", width=4)
    d.polygon([(542, 711), (558, 702), (558, 720)], fill="#d04b3e")
    d.text((178, 704), "A", font=_police(20, True), fill="#3978a8")
    d.text((615, 700), "B", font=_police(20, True), fill="#d04b3e")

    d.rectangle([700, 648, 1056, 770], outline="#77736c")
    d.text((716, 660), "Signatures des conducteurs", font=_police(14, True), fill="#4d4943")
    d.text((716, 704), "A : Ahmed Ben Salah", font=_police(15), fill="#202020")
    d.text((716, 738), "B : Mohamed R.", font=_police(15), fill="#202020")
    img.save(chemin, quality=92)
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
    d.text((40, 1050), "Croquis d'expertise établi sur constatations",
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

    # Les photos réelles de dégâts sont des assets versionnés : ne jamais les
    # écraser lors de la régénération des documents.
    _constat(DOSSIER / "constat.jpg")
    print("OK — documents régénérés ; photos réelles conservées")


if __name__ == "__main__":
    generer()
