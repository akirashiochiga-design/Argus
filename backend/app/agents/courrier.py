"""Agent 7 — Rédaction du courrier de décision (LLM texte).

Le montant et la décision sont IMPOSÉS par le calcul déterministe et la
décision humaine — ils sont injectés dans le prompt, jamais calculés ici.
Fallback simulation : lettre à trous déterministe.
"""
from sqlmodel import Session, select

from .. import llm
from ..models import Agent, Dossier, Police, Tache


def _contexte(dossier: Dossier, session: Session) -> dict:
    police = session.get(Police, dossier.police_id)
    tache = session.exec(
        select(Tache).where(Tache.dossier_id == dossier.id).order_by(Tache.id.desc())
    ).first()
    position = dossier.position_couverture or {}
    return {
        "assure": police.assure_nom,
        "police": police.numero,
        "decision": (tache.decision if tache else None) or "approuver",
        "motif_humain": tache.motif if tache else None,
        "couvert": position.get("couvert"),
        "clauses": [m["clause"] for m in position.get("motivation", [])],
        "motivation": position.get("motivation", []),
        "montant": dossier.montant_valide,
        "langue": (dossier.donnees_fnol or {}).get("langue", "fr"),
    }


def _fallback(ctx: dict, dossier: Dossier) -> dict:
    if ctx["decision"] == "sans_suite":
        objet = f"Sinistre {dossier.ref} — dossier clôturé sans suite"
        corps = (
            f"Madame, Monsieur {ctx['assure']},\n\n"
            f"Malgré notre relance concernant les pièces nécessaires au traitement de votre "
            f"déclaration (police {ctx['police']}), nous restons sans réponse de votre part.\n\n"
            + (f"Précision du gestionnaire : {ctx['motif_humain']}\n\n" if ctx["motif_humain"] else "") +
            "Nous clôturons donc ce dossier sans suite. Vous pouvez le rouvrir à tout moment en "
            "nous transmettant les pièces manquantes.\n\nCordialement,\nService Sinistres"
        )
        return {"objet": objet, "corps": corps}
    if ctx["decision"] == "refuser" or not ctx["couvert"]:
        objet = f"Sinistre {dossier.ref} — décision de refus"
        corps = (
            f"Madame, Monsieur {ctx['assure']},\n\n"
            f"Après étude de votre déclaration (police {ctx['police']}), nous ne pouvons donner "
            f"une suite favorable à votre demande d'indemnisation.\n\n"
            f"Motifs :\n" + "\n".join(f"  - {m['conclusion']} ({m['clause']})" for m in ctx["motivation"]) +
            ("\n\nComplément du gestionnaire : " + ctx["motif_humain"] if ctx["motif_humain"] else "") +
            "\n\nVous disposez d'un délai de recours de 30 jours.\n\nCordialement,\nService Sinistres"
        )
    else:
        objet = f"Sinistre {dossier.ref} — accord d'indemnisation ({ctx['montant']} DT)"
        corps = (
            f"Madame, Monsieur {ctx['assure']},\n\n"
            f"Nous avons le plaisir de vous informer que votre sinistre (police {ctx['police']}) "
            f"est pris en charge.\n\n"
            f"Montant validé : {ctx['montant']} DT, calculé selon :\n" +
            "\n".join(f"  - {m['conclusion']} ({m['clause']})" for m in ctx["motivation"]) +
            "\n\nLe règlement sera effectué sous 5 jours ouvrés.\n\nCordialement,\nService Sinistres"
        )
    return {"objet": objet, "corps": corps}


def executer(agent: Agent, dossier: Dossier, session: Session) -> dict:
    ctx = _contexte(dossier, session)
    prompt = (
        "Rédige la lettre de décision pour l'assuré à partir de ces éléments VÉRIFIÉS. "
        "N'invente aucun montant ni aucune clause : reprends exactement ceux fournis.\n\n"
        f"Assuré : {ctx['assure']} — Police : {ctx['police']} — Dossier : {dossier.ref}\n"
        f"Décision humaine : {ctx['decision']}"
        + (f" (motif : {ctx['motif_humain']})" if ctx['motif_humain'] else "") + "\n"
    )
    if ctx["decision"] == "sans_suite":
        prompt += (
            "Ce dossier est clôturé SANS SUITE : l'assuré n'a pas fourni les pièces demandées "
            "malgré relance. Rédige un courrier de clôture courtois qui explique la raison et "
            "précise que le dossier peut être rouvert en transmettant les pièces manquantes. "
            "N'invente et ne mentionne aucun montant.\n"
        )
    else:
        prompt += (
            f"Couvert : {ctx['couvert']}\n"
            f"Montant validé : {ctx['montant']} DT\n"
            f"Motivation ligne à ligne : {ctx['motivation']}\n"
        )
    prompt += (
        f"Langue de l'assuré : {ctx['langue']} (écris la lettre en français, ton courtois et clair, "
        "et si la langue est 'darija', ajoute une phrase de synthèse finale en arabe tunisien translittéré).\n\n"
        "Réponds au format : première ligne = objet, puis une ligne vide, puis le corps."
    )
    try:
        resultat = llm.generer_texte(agent.instructions, prompt)
        lignes = resultat["texte"].split("\n", 1)
        courrier = {
            "objet": lignes[0].removeprefix("Objet :").strip(),
            "corps": lignes[1].strip() if len(lignes) > 1 else resultat["texte"],
            "mode": "llm",
        }
        meta = {"cout": resultat["cout"], "duree_ms": resultat["duree_ms"], "mode": "llm"}
    except llm.LLMIndisponible:
        courrier = {**_fallback(ctx, dossier), "mode": "simulation"}
        meta = {"cout": 0.0, "duree_ms": 5, "mode": "simulation"}

    return {"courrier": courrier, "confiance": 0.95, **meta}
