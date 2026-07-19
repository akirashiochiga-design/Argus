"""Tests du composeur de traitements métier."""
import unittest

from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.connectors.insurance_sqlite import synchroniser
from app.models import Agent, Dossier, Workflow
from app.routers.agents import (
    TraitementEntrant,
    activer_workflow,
    creer_workflow,
)
from app.workflow_service import traitement_actif, valider_etapes


class WorkflowComposerTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.modules = {}
        for categorie in (
            "fnol",
            "extraction",
            "vision",
            "garanties",
            "indemnite",
            "hitl",
            "courrier",
        ):
            module = Agent(
                nom=f"Module {categorie}",
                categorie=categorie,
                statut="live",
            )
            self.session.add(module)
            self.session.flush()
            self.modules[categorie] = module
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def ids_standard(self) -> list[int]:
        return [
            self.modules[categorie].id
            for categorie in (
                "fnol",
                "extraction",
                "vision",
                "garanties",
                "indemnite",
                "hitl",
                "courrier",
            )
        ]

    def test_creation_et_activation_traitement(self):
        traitement = creer_workflow(
            TraitementEntrant(
                nom="Collision renforcée",
                description="Contrôles complets",
                agent_ids=self.ids_standard(),
            ),
            self.session,
        )
        self.assertEqual(len(traitement.etapes), 7)
        self.assertEqual(traitement.etapes[5]["type"], "porte_humaine")
        actif = activer_workflow(traitement.id, self.session)
        self.assertTrue(actif.est_defaut)
        self.assertEqual(traitement_actif(self.session).id, traitement.id)

    def test_validation_gestionnaire_est_obligatoire(self):
        ids = [
            module_id
            for module_id in self.ids_standard()
            if module_id != self.modules["hitl"].id
        ]
        with self.assertRaises(HTTPException) as contexte:
            creer_workflow(
                TraitementEntrant(
                    nom="Traitement invalide",
                    agent_ids=ids,
                ),
                self.session,
            )
        self.assertEqual(contexte.exception.status_code, 422)
        self.assertIn("validation gestionnaire", contexte.exception.detail)

    def test_module_personnalise_peut_etre_utilise(self):
        personnalise = Agent(
            nom="Contrôle photos renforcé",
            categorie="vision",
            statut="live",
            garde_fous={"origine": "prompt_studio"},
        )
        self.session.add(personnalise)
        self.session.commit()
        ids = [
            personnalise.id if identifiant == self.modules["vision"].id else identifiant
            for identifiant in self.ids_standard()
        ]
        etapes = valider_etapes(self.session, ids)
        self.assertIn(personnalise.id, [etape["agent_id"] for etape in etapes])

    def test_synchronisation_utilise_le_traitement_actif(self):
        premier = Workflow(
            nom="Ancien traitement",
            statut="live",
            est_defaut=False,
            etapes=valider_etapes(self.session, self.ids_standard()),
        )
        actif = Workflow(
            nom="Traitement actif",
            statut="live",
            est_defaut=True,
            etapes=valider_etapes(self.session, self.ids_standard()),
        )
        self.session.add(premier)
        self.session.add(actif)
        self.session.commit()
        synchroniser(self.session)
        dossiers = self.session.exec(select(Dossier)).all()
        self.assertEqual(len(dossiers), 3)
        self.assertTrue(all(dossier.workflow_id == actif.id for dossier in dossiers))


if __name__ == "__main__":
    unittest.main()
