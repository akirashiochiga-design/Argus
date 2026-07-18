# Fichiers d'exemple pour la démo

**Documents fictifs réalistes** (par `python -m app.samples`, régénérables à volonté) :
`facture.jpg` (2 300 DT — calibrée pour SIN-2026-001), `devis.jpg` (1 750 DT),
`devis-parebrise.jpg` (420 DT), `constat.jpg`. L'agent extraction vision les lit
réellement dès qu'une clé API est présente.

**Photos réelles libres d'usage** :

- `degats-1.jpg`, `degats-2.jpg` — dégâts avant droit (pare-chocs, phare, aile), cohérents avec SIN-2026-001.
- `parebrise.jpg` — pare-brise fissuré. Elle est volontairement aussi jointe à SIN-2026-001 :
  c'est la pièce incohérente utilisée pour démontrer l'agent « cohérence déclaration / photos ».
- `degats-3.jpg` — véhicule fortement endommagé : cohérent avec le choc frontal de
  SIN-2026-002, mais volontairement incohérent avec la légère rayure arrière déclarée
  dans SIN-2026-004.

Sources : Pexels, photos 10747780, 7857825, 11627936 et 19773544,
utilisées conformément à la licence Pexels.

Les chemins sont référencés dans `backend/app/seed.py` (champ `pieces` des dossiers).
