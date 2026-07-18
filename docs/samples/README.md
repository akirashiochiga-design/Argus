# Fichiers d'exemple pour la démo

À déposer ici AVANT samedi matin (et à tester avec le prompt vision avant la démo) :

- `constat.jpg` — un constat amiable rempli (photo ou scan)
- `facture.jpg` — facture de réparation du garage, **montant total ≈ 2 300 DT**
  (le calcul du dossier SIN-2026-001 est calibré dessus : 2 300 − 10 % vétusté − 220 franchise = 1 850 DT)
- `degats-1.jpg`, `degats-2.jpg` — photos de dégâts avant droit (pare-chocs, phare, aile) — gravité attendue : moyen
- `degats-3.jpg` — photos capot/pare-chocs enfoncés (dossier SIN-2026-002)
- `parebrise.jpg` + `devis-parebrise.jpg` — fissure pare-brise + devis ≈ 420 DT (dossier SIN-2026-003)

Les chemins sont référencés dans `backend/app/seed.py` (champ `pieces` des dossiers).
