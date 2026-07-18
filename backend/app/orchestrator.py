"""Moteur d'orchestration — machine à états maison, lisible à 3h du matin.

Un appel à avancer() exécute UNE étape du workflow et s'arrête :
c'est le frontend qui enchaîne les appels (animation de la vue Pipeline).
La porte humaine suspend le pipeline ; seule une décision humaine
(decider()) le relance. Chaque étape écrit un Run + un EvenementAudit.

Invariants codés en dur :
- l'état "regle" n'est atteignable que via une décision humaine ;
- la porte humaine n'appelle jamais llm.py ;
- toute transition d'état passe par audit.tracer().
"""
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session

from . import agents
from .audit import tracer
from .models import Agent, Dossier, Run, Tache, Workflow

# Champs de sortie d'agent que l'orchestrateur reporte sur le dossier
CHAMPS_DOSSIER = (
    "donnees_fnol", "pieces", "montant_estime", "gravite",
    "position_couverture", "montant_recommande", "courrier",
)

# Valeurs par défaut pour rejouer proprement l'état lors d'un retour arrière.
# montant_valide en est ABSENT : c'est une donnée humaine, pas une sortie d'agent.
CHAMPS_DEFAUT = {
    "donnees_fnol": {}, "gravite": None, "position_couverture": {},
    "montant_estime": None, "montant_recommande": None, "courrier": {},
}

ETATS_TERMINES = ("regle", "refuse", "cloture")


class OrchestrationErreur(Exception):
    def __init__(self, code: int, detail: str):
        self.code = code
        self.detail = detail


def _changer_etat(session: Session, dossier: Dossier, nouvel_etat: str, acteur: str, motif: str = None) -> None:
    if dossier.etat == nouvel_etat:
        return
    avant = dossier.etat
    dossier.etat = nouvel_etat
    tracer(
        session, acteur=acteur, acteur_type="agent" if acteur.startswith("agent:") else "humain",
        type="changement_etat", objet=f"dossier:{dossier.ref}",
        avant={"etat": avant}, apres={"etat": nouvel_etat}, motif=motif,
    )


def avancer(session: Session, dossier: Dossier) -> dict:
    """Exécute la prochaine étape du workflow du dossier. Retourne un résumé pour l'UI."""
    if dossier.etat in ETATS_TERMINES:
        raise OrchestrationErreur(409, f"Dossier {dossier.ref} déjà en état '{dossier.etat}'")
    if dossier.etat == "attente_validation":
        raise OrchestrationErreur(409, "En attente d'une décision humaine — voir la file d'approbation")

    workflow = session.get(Workflow, dossier.workflow_id)
    if not workflow or dossier.etape_courante >= len(workflow.etapes):
        raise OrchestrationErreur(409, "Aucune étape restante dans le workflow")

    etape = workflow.etapes[dossier.etape_courante]
    agent = session.get(Agent, etape["agent_id"])
    acteur = f"agent:{agent.nom} v{agent.version}"

    # ---- Exécution de l'agent (porte humaine incluse : elle crée la Tache) ----
    executer = agents.DISPATCH[agent.categorie]
    instantane_avant = {"etat": dossier.etat, "etape": dossier.etape_courante}
    try:
        sorties = executer(agent, dossier, session)
        statut_run = "succes"
    except Exception as e:  # un agent qui plante ne doit pas casser la démo
        sorties = {"erreur": str(e)}
        statut_run = "echec"

    run = Run(
        dossier_id=dossier.id,
        agent_id=agent.id,
        entrees={"etape": etape, "etat_dossier": instantane_avant["etat"]},
        sorties=sorties,
        statut=statut_run,
        confiance=sorties.get("confiance"),
        cout=sorties.get("cout", 0.0),
        duree_ms=sorties.get("duree_ms", 0),
    )
    session.add(run)

    if statut_run == "echec":
        tracer(session, acteur, "agent", "run_agent", f"dossier:{dossier.ref}",
               avant=instantane_avant, apres={"statut": "echec", "erreur": sorties.get("erreur")})
        session.commit()
        raise OrchestrationErreur(500, f"Échec de l'agent '{agent.nom}' : {sorties.get('erreur')}")

    # ---- Application des sorties au dossier ----
    for champ in CHAMPS_DOSSIER:
        if champ in sorties and sorties[champ] is not None:
            setattr(dossier, champ, sorties[champ])

    tracer(session, acteur, "agent", "run_agent", f"dossier:{dossier.ref}",
           avant=instantane_avant,
           apres={k: v for k, v in sorties.items() if k in (*CHAMPS_DOSSIER, "tache_id", "routage", "montant_recommande")})

    # ---- Transition ----
    if etape["type"] == "porte_humaine":
        _changer_etat(session, dossier, "attente_validation", acteur, motif=sorties.get("routage"))
        dossier.etape_courante += 1  # la reprise post-décision part de l'étape suivante
        session.commit()
        session.refresh(dossier)
        session.refresh(run)
        return {"resultat": "porte_humaine", "run": run.model_dump(), "dossier": dossier.model_dump(),
                "tache_id": sorties.get("tache_id"), "agent": agent.nom}

    dossier.etape_courante += 1
    terminee = dossier.etape_courante >= len(workflow.etapes)
    if terminee:
        etat_final = _etat_final(session, dossier)
        _changer_etat(session, dossier, etat_final, acteur, motif="pipeline terminé")
    else:
        _changer_etat(session, dossier, "en_cours", acteur)

    session.commit()
    session.refresh(dossier)
    session.refresh(run)
    return {"resultat": "termine" if terminee else "etape_executee",
            "run": run.model_dump(), "dossier": dossier.model_dump(), "agent": agent.nom}


def _etat_final(session: Session, dossier: Dossier) -> str:
    """L'état final découle de la décision HUMAINE enregistrée — jamais d'un agent.

    validation_reglement : approuver/modifier → réglé ; refuser → refusé.
    validation_refus     : approuver = confirmer le refus → refusé ;
                           modifier (dérogation avec montant) → réglé.
    demande_piece        : modifier (pièce reçue, montant saisi) → réglé ;
                           sans_suite (assuré non-répondant) → clôturé, quel
                           que soit le type de tâche à l'origine.
    """
    from sqlmodel import select
    tache = session.exec(
        select(Tache).where(Tache.dossier_id == dossier.id).order_by(Tache.id.desc())
    ).first()
    if not tache or tache.etat != "decidee":
        return "refuse"
    if tache.decision == "sans_suite":
        return "cloture"
    if tache.type == "validation_refus":
        return "regle" if tache.decision == "modifier" else "refuse"
    return "regle" if tache.decision in ("approuver", "modifier") else "refuse"


def reculer(session: Session, dossier: Dossier) -> dict:
    """Annule la dernière étape exécutée — utile pour rejouer un dossier en démo.

    Retire le dernier Run, rejoue l'état des champs depuis les runs restants
    (reconstruction déterministe, pas d'undo champ par champ fragile), et
    supprime la tâche + le montant validé si l'étape annulée était la porte
    humaine. Tracé dans l'audit comme tout le reste.
    """
    from sqlmodel import select

    runs = session.exec(
        select(Run).where(Run.dossier_id == dossier.id).order_by(Run.id)
    ).all()
    if not runs:
        raise OrchestrationErreur(409, "Rien à annuler — le dossier est au début du pipeline")

    dernier = runs[-1]
    agent = session.get(Agent, dernier.agent_id)
    avant = {"etat": dossier.etat, "etape": dossier.etape_courante, "agent": agent.nom if agent else None}

    # Si on annule la porte humaine, on efface sa tâche et la décision associée
    if agent and agent.categorie == "hitl":
        for t in session.exec(select(Tache).where(Tache.dossier_id == dossier.id)).all():
            session.delete(t)
        dossier.montant_valide = None

    session.delete(dernier)
    restants = runs[:-1]

    # Reconstruire l'état des champs à partir des runs conservés
    for champ, defaut in CHAMPS_DEFAUT.items():
        setattr(dossier, champ, defaut)
    for r in restants:
        if r.statut != "succes":
            continue
        for champ in CHAMPS_DOSSIER:
            if champ in r.sorties and r.sorties[champ] is not None:
                setattr(dossier, champ, r.sorties[champ])

    dossier.etape_courante = max(0, dossier.etape_courante - 1)
    dossier.etat = "recu" if dossier.etape_courante == 0 else "en_cours"

    tracer(
        session, acteur="humain:superviseur", acteur_type="humain",
        type="retour_arriere", objet=f"dossier:{dossier.ref}",
        avant=avant, apres={"etat": dossier.etat, "etape": dossier.etape_courante},
        motif=f"annulation de l'étape « {agent.nom if agent else '?'} »",
    )
    session.commit()
    session.refresh(dossier)
    return {"resultat": "recule", "dossier": dossier.model_dump(), "agent_annule": agent.nom if agent else None}


def decider(session: Session, tache: Tache, decision: str, validateur: str,
            montant: Optional[float] = None, motif: Optional[str] = None) -> dict:
    """Décision humaine sur une tâche : approuver / modifier / refuser / sans_suite.

    C'est LE seul chemin vers un règlement. L'écart montant validé vs
    recommandé alimente le taux de correction du dashboard.

    'sans_suite' est la capacité d'adaptation pour le cas "l'assuré ne
    répond pas" (ou toute impasse similaire) : le dossier est clôturé sans
    règlement ni refus formel, motivé, tracé, et un courrier de clôture est
    quand même généré. Distinct de 'refuser' : ce n'est pas un rejet de la
    garantie, c'est une impossibilité de conclure faute de réponse.
    """
    if tache.etat == "decidee":
        raise OrchestrationErreur(409, "Tâche déjà décidée")
    if decision not in ("approuver", "modifier", "refuser", "sans_suite"):
        raise OrchestrationErreur(400, "Décision invalide (approuver|modifier|refuser|sans_suite)")
    if decision == "modifier" and montant is None:
        raise OrchestrationErreur(400, "Un montant est requis pour 'modifier'")
    if decision in ("refuser", "sans_suite") and not motif:
        raise OrchestrationErreur(400, "Un motif est requis pour cette décision")

    dossier = session.get(Dossier, tache.dossier_id)

    tache.decision = decision
    tache.motif = motif
    tache.validateur = validateur
    tache.etat = "decidee"
    tache.decide_le = datetime.now(timezone.utc)

    if decision == "modifier":
        dossier.montant_valide = float(montant)
    elif decision == "approuver" and tache.type == "validation_reglement":
        dossier.montant_valide = tache.montant
    else:  # refus, ou confirmation d'un refus proposé
        dossier.montant_valide = None

    tracer(
        session, acteur=f"humain:{validateur}", acteur_type="humain",
        type="decision_humaine", objet=f"tache:{tache.id}",
        avant={"montant_recommande": tache.montant, "dossier": dossier.ref},
        apres={"decision": decision, "montant_valide": dossier.montant_valide},
        motif=motif,
    )

    # Le pipeline repart (étape courrier) — l'état final sera posé à la fin
    _changer_etat(session, dossier, "en_cours", f"humain:{validateur}",
                  motif=f"décision '{decision}' — reprise du pipeline")
    session.commit()
    session.refresh(tache)
    session.refresh(dossier)
    return {"tache": tache.model_dump(), "dossier": dossier.model_dump()}
