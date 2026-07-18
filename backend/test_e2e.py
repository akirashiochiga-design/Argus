"""Test de bout en bout du pipeline Argus — rejouable avant chaque répétition.

Usage :  .venv/Scripts/python test_e2e.py   (backend démarré sur :8000)
Réinitialise la base, déroule les 3 dossiers seed + 1 déclaration live,
vérifie chaque invariant (montants, états, audit, studio). Sort en erreur
au premier écart — si ce script passe, la démo passe.
"""
import json
import sys
import urllib.request

BASE = "http://localhost:8000"
ECHECS = []


def appel(methode: str, chemin: str, corps: dict = None) -> dict | list:
    donnees = json.dumps(corps).encode("utf-8") if corps is not None else None
    req = urllib.request.Request(
        BASE + chemin, data=donnees, method=methode,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as rep:
            return json.loads(rep.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"__erreur__": e.code, "detail": e.read().decode("utf-8")}


def verifier(nom: str, condition: bool, detail: str = ""):
    statut = "OK " if condition else "ECHEC"
    print(f"  [{statut}] {nom}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        ECHECS.append(nom)


def executer_pipeline(dossier_id: int, max_etapes: int = 8) -> dict:
    """Enchaîne /executer jusqu'à porte humaine ou fin."""
    resultat = {}
    for _ in range(max_etapes):
        resultat = appel("POST", f"/dossiers/{dossier_id}/executer")
        if "__erreur__" in resultat or resultat.get("resultat") in ("porte_humaine", "termine"):
            break
    return resultat


print("=== 0. Reset démo ===")
r = appel("POST", "/admin/reseed")
verifier("reseed", r.get("statut") == "ok")

print("=== 1. Dossier vedette SIN-2026-001 : 1 850 DT, validation obligatoire ===")
r = executer_pipeline(1)
verifier("pipeline suspendu à la porte humaine", r.get("resultat") == "porte_humaine")
d = appel("GET", "/dossiers/1")["dossier"]
verifier("montant recommandé = 1850.0", d["montant_recommande"] == 1850.0, str(d["montant_recommande"]))
verifier("état = attente_validation", d["etat"] == "attente_validation", d["etat"])
verifier("couvert = true", d["position_couverture"]["couvert"] is True)
taches = appel("GET", "/taches?etat=en_attente")
t1 = next(t for t in taches if t["dossier_ref"] == "SIN-2026-001")
verifier("tâche au-dessus du seuil (validation obligatoire)", t1["proposition"]["sous_seuil"] is False)
verifier("détail du calcul présent dans la proposition", len(t1["proposition"]["detail_calcul"]) >= 4)

r = appel("POST", f"/taches/{t1['id']}/decider",
          {"decision": "approuver", "validateur": "Selma (superviseure)"})
verifier("décision enregistrée", r["tache"]["decision"] == "approuver")
r = executer_pipeline(1)
verifier("pipeline terminé", r.get("resultat") == "termine")
d = appel("GET", "/dossiers/1")["dossier"]
verifier("état final = regle", d["etat"] == "regle", d["etat"])
verifier("montant validé = 1850.0", d["montant_valide"] == 1850.0)
verifier("courrier généré", bool(d["courrier"].get("corps")))

print("=== 2. SIN-2026-002 : formule tiers -> refus motivé, confirmé par l'humain ===")
executer_pipeline(2)
d = appel("GET", "/dossiers/2")["dossier"]
verifier("non couvert", d["position_couverture"]["couvert"] is False)
verifier("clause citée dans la motivation",
         any("Art." in m["clause"] for m in d["position_couverture"]["motivation"]))
t2 = next(t for t in appel("GET", "/taches?etat=en_attente") if t["dossier_ref"] == "SIN-2026-002")
verifier("tâche de type validation_refus", t2["type"] == "validation_refus")
appel("POST", f"/taches/{t2['id']}/decider",
      {"decision": "approuver", "validateur": "Selma (superviseure)",
       "motif": "Garantie collision absente de la formule tiers"})
executer_pipeline(2)
d = appel("GET", "/dossiers/2")["dossier"]
verifier("état final = refuse", d["etat"] == "refuse", d["etat"])
verifier("courrier de refus généré", "refus" in d["courrier"].get("objet", "").lower())

print("=== 3. SIN-2026-003 : 420 DT sous le seuil -> proposé, humain approuve ===")
executer_pipeline(3)
t3 = next(t for t in appel("GET", "/taches?etat=en_attente") if t["dossier_ref"] == "SIN-2026-003")
verifier("montant = 420.0", t3["montant"] == 420.0, str(t3["montant"]))
verifier("routage sous seuil (proposé)", t3["proposition"]["sous_seuil"] is True)
appel("POST", f"/taches/{t3['id']}/decider", {"decision": "approuver", "validateur": "Selma (superviseure)"})
executer_pipeline(3)
verifier("état final = regle", appel("GET", "/dossiers/3")["dossier"]["etat"] == "regle")

print("=== 4. Garde-fou : impossible d'exécuter un dossier réglé ===")
r = appel("POST", "/dossiers/1/executer")
verifier("409 sur dossier réglé", r.get("__erreur__") == 409)

print("=== 5. Studio : créer -> publier -> AJOUTER (pas remplacer), et modifier un seuil ===")
wf_avant = appel("GET", "/workflows")[0]
nb_etapes_avant = len(wf_avant["etapes"])
a = appel("POST", "/agents", {"nom": "Règlement auto — bris de glace", "template_id": 3,
                              "seuils": {"seuil_validation": 300}})
verifier("agent créé en draft", a.get("statut") == "draft", str(a))
r = appel("POST", "/workflows/1/ajouter-etape", {"agent_id": a["id"]})
verifier("ajouter un draft est refusé (409)", r.get("__erreur__") == 409)
a2 = appel("POST", f"/agents/{a['id']}/publier")
verifier("agent publié live", a2["statut"] == "live")
w = appel("POST", "/workflows/1/ajouter-etape", {"agent_id": a["id"]})
verifier("agent présent dans le pipeline", any(e["agent_id"] == a["id"] for e in w.get("etapes", [])))
verifier("le pipeline compte UNE étape de PLUS qu'avant (ajout, pas remplacement)",
         len(w["etapes"]) == nb_etapes_avant + 1, f"{len(w['etapes'])} vs {nb_etapes_avant}")
verifier("l'agent d'origine 'Calcul indemnité auto' (id 5) est toujours présent",
         any(e["agent_id"] == 5 for e in w["etapes"]))
r = appel("POST", "/workflows/1/ajouter-etape", {"agent_id": a["id"]})
verifier("ajouter deux fois le même agent est refusé (409)", r.get("__erreur__") == 409)
h = appel("PATCH", "/agents/6", {"seuils": {"seuil_validation": 300, "plafond_auto": 200}})
verifier("seuil HITL modifié, version incrémentée", h["seuils"]["seuil_validation"] == 300 and h["version"] == 2)
avant_instr = appel("GET", "/agents")
agent5_avant = next(x for x in avant_instr if x["id"] == 5)
i = appel("PATCH", "/agents/5", {"instructions": "Calcule le montant en franchisant systématiquement 50 DT de plus."})
verifier("instructions d'un agent DE BASE modifiables séparément (action distincte)",
         i["instructions"] != agent5_avant["instructions"] and i["version"] == agent5_avant["version"] + 1)

print("=== 6. Déclaration live -> nouveau seuil appliqué (380 DT >= 300 -> validation) ===")
d4 = appel("POST", "/dossiers", {
    "declaration_texte": "Bonjour, un caillou a fissuré mon pare-brise ce matin sur la GP1. "
                         "Je joins le devis (380 DT). Mohamed Gharbi, police PA-2025-0212.",
    "police_numero": "PA-2025-0212",
    "pieces": [{"type": "devis", "chemin": "docs/samples/devis-parebrise.jpg", "montant": 380}],
})
verifier("dossier créé", d4.get("ref", "").startswith("SIN-2026-"), str(d4))
executer_pipeline(d4["id"])
t4 = next(t for t in appel("GET", "/taches?etat=en_attente") if t["dossier_ref"] == d4["ref"])
verifier("380 DT >= nouveau seuil 300 -> validation obligatoire", t4["proposition"]["sous_seuil"] is False)
appel("POST", f"/taches/{t4['id']}/decider",
      {"decision": "modifier", "montant": 350.0, "validateur": "Selma (superviseure)",
       "motif": "Vétusté du joint non indemnisable"})
executer_pipeline(d4["id"])
d = appel("GET", f"/dossiers/{d4['id']}")["dossier"]
verifier("montant modifié par l'humain = 350.0", d["montant_valide"] == 350.0)
verifier("état final = regle", d["etat"] == "regle")

print("=== 7. Audit & KPI ===")
audit = appel("GET", "/audit?limit=500")
verifier("piste d'audit fournie (>= 40 événements)", len(audit) >= 40, str(len(audit)))
verifier("décisions humaines tracées", any(e["type"] == "decision_humaine" for e in audit))
verifier("création d'agent tracée", any(e["type"] == "creation_agent" for e in audit))
verifier("modification de seuil tracée", any(e["type"] == "modification_agent" for e in audit))
kpi = appel("GET", "/dashboard/kpi")
verifier("4 dossiers traités", kpi["dossiers_traites"] == 4, str(kpi["dossiers_traites"]))
verifier("taux de correction > 0 (décision 'modifier')", kpi["taux_correction"] > 0)

print("=== 8. Retour arrière & rejeu (contrôles de démo) ===")
appel("POST", "/admin/reseed")
executer_pipeline(1)  # dossier 1 -> attente_validation (6 runs)
avant = appel("GET", "/dossiers/1")["dossier"]
verifier("dossier 1 en attente avant recul", avant["etat"] == "attente_validation")
r = appel("POST", "/dossiers/1/reculer")
verifier("reculer annule la porte humaine", r["agent_annule"] == "Porte de validation humaine")
d = appel("GET", "/dossiers/1")["dossier"]
verifier("état revenu à en_cours", d["etat"] == "en_cours")
verifier("plus de tâche en attente après recul",
         not any(t["dossier_ref"] == "SIN-2026-001" for t in appel("GET", "/taches?etat=en_attente")))
appel("POST", "/dossiers/1/reculer")  # annule le calcul indemnité
d = appel("GET", "/dossiers/1")["dossier"]
verifier("montant recommandé effacé après recul du calcul", d["montant_recommande"] is None)
r = appel("POST", "/dossiers/1/rejouer")
verifier("rejouer remet à l'étape 0", r["dossier"]["etape_courante"] == 0 and r["dossier"]["etat"] == "recu")
verifier("aucun run après rejeu", len(appel("GET", "/dossiers/1")["runs"]) == 0)

print("=== 9. Studio : agent personnalisé depuis un prompt ===")
cats = appel("GET", "/studio/categories")
verifier("catégories argent NON proposées au prompt",
         "garanties" not in cats and "indemnite" not in cats and "hitl" not in cats)
gen = appel("POST", "/studio/generer-instructions", {"brief": "vérifier la cohérence photos / déclaration"})
verifier("instructions générées (llm ou simulation)", len(gen["instructions"]) > 40 and gen["mode"] in ("llm", "simulation"))
ap = appel("POST", "/studio/agents-personnalises",
           {"nom": "Contrôle cohérence", "categorie": "vision", "instructions": gen["instructions"]})
verifier("agent personnalisé créé en draft", ap.get("statut") == "draft")
verifier("garde-fou argent imposé sur l'agent perso", ap["garde_fous"].get("pas_de_decision_argent") is True)
r = appel("POST", "/studio/agents-personnalises",
          {"nom": "Triche", "categorie": "indemnite", "instructions": "calcule le montant"})
verifier("catégorie argent refusée (400)", r.get("__erreur__") == 400)

print("=== 10. Capacité d'adaptation : pièce manquante -> demande_piece -> sans_suite ===")
appel("POST", "/admin/reseed")
d4 = next(x for x in appel("GET", "/dossiers") if x["ref"] == "SIN-2026-004")
verifier("SIN-2026-004 démarre sans pièce chiffrée", d4["montant_estime"] is None)
executer_pipeline(d4["id"])
t5 = next(t for t in appel("GET", "/taches?etat=en_attente") if t["dossier_ref"] == "SIN-2026-004")
verifier("tâche de type demande_piece (pas un faux règlement à 0 DT)", t5["type"] == "demande_piece", t5["type"])
r = appel("POST", f"/taches/{t5['id']}/decider", {"decision": "sans_suite", "validateur": "Selma (superviseure)"})
verifier("motif obligatoire pour 'sans_suite' (400 si absent)", r.get("__erreur__") == 400)
appel("POST", f"/taches/{t5['id']}/decider",
      {"decision": "sans_suite", "validateur": "Selma (superviseure)",
       "motif": "Relance envoyée le 20/07, aucune réponse sous 15 jours"})
executer_pipeline(d4["id"])
d = appel("GET", f"/dossiers/{d4['id']}")["dossier"]
verifier("état final = cloture (ni réglé ni refusé)", d["etat"] == "cloture", d["etat"])
verifier("montant validé reste vide", d["montant_valide"] is None)
verifier("courrier de clôture généré", "clôturé" in d["courrier"].get("objet", "").lower(), d["courrier"])

print("=== 11. Relance de l'assuré avant clôture sans suite ===")
appel("POST", "/admin/reseed")
d4b = next(x for x in appel("GET", "/dossiers") if x["ref"] == "SIN-2026-004")
executer_pipeline(d4b["id"])
t6 = next(t for t in appel("GET", "/taches?etat=en_attente") if t["dossier_ref"] == "SIN-2026-004")
r = appel("POST", f"/taches/{t6['id']}/relancer", {"validateur": "Selma (superviseure)"})
verifier("relance envoyée, message généré (email simulé ou IA)",
         len(r["tache"]["relances"]) == 1 and bool(r["tache"]["relances"][0].get("objet")))
r2 = appel("POST", f"/taches/{t6['id']}/relancer", {"validateur": "Selma (superviseure)"})
verifier("une deuxième relance s'ajoute à l'historique (pas de remplacement)",
         len(r2["tache"]["relances"]) == 2)
r_apres_decision = appel("POST", f"/taches/{t6['id']}/decider",
                          {"decision": "sans_suite", "validateur": "Selma (superviseure)",
                           "motif": "Relance envoyée le 20/07, aucune réponse sous 15 jours"})
r3 = appel("POST", f"/taches/{t6['id']}/relancer", {"validateur": "Selma (superviseure)"})
verifier("relancer une tâche déjà décidée est refusé (409)", r3.get("__erreur__") == 409)
executer_pipeline(d4b["id"])
d = appel("GET", f"/dossiers/{d4b['id']}")["dossier"]
verifier("état final = cloture", d["etat"] == "cloture", d["etat"])
audit = appel("GET", "/audit?limit=500")
verifier("relance tracée dans l'audit", any(e["type"] == "relance_assure" for e in audit))

print()
if ECHECS:
    print(f"{len(ECHECS)} ECHEC(S) : {ECHECS}")
    sys.exit(1)
print("TOUS LES TESTS PASSENT — la demo est prete. (Relancer /admin/reseed avant de presenter.)")
