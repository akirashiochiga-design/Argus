# Fichiers d'exemple pour la démo

**Déjà générés** (par `python -m app.samples`, régénérables à volonté) :
`facture.jpg` (2 300 DT — calibrée pour SIN-2026-001), `devis.jpg` (1 750 DT),
`devis-parebrise.jpg` (420 DT), `constat.jpg`. L'agent extraction vision les lit
réellement dès qu'une clé API est présente. Remplacez-les par de vrais scans si possible.

**À déposer manuellement AVANT la démo** (photos réelles, testées avec la clé API) :

- `degats-1.jpg`, `degats-2.jpg` — dégâts avant droit (pare-chocs, phare, aile) — gravité attendue : moyen
- `degats-3.jpg` — capot/pare-chocs enfoncés (dossier SIN-2026-002)
- `parebrise.jpg` — fissure de pare-brise (dossier SIN-2026-003)

Sans photos, l'agent gravité bascule en estimation sur la déclaration (confiance
réduite, note explicite) — la démo fonctionne quand même.

Les chemins sont référencés dans `backend/app/seed.py` (champ `pieces` des dossiers).
