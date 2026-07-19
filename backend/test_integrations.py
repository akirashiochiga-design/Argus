"""Tests du connecteur fonctionnel vers la base assurance externe."""
import unittest

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.connectors.insurance_sqlite import apercu, synchroniser, tester_connexion
from app.models import Dossier, EvenementAudit, Police, Workflow


class IntegrationAssuranceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.session.add(Workflow(nom="Parcours test", statut="live", etapes=[]))
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_schema_externe_est_reellement_accessible(self):
        resultat = tester_connexion()
        self.assertEqual(resultat["statut"], "connecte")
        self.assertEqual(resultat["compteurs"]["polices"], 4)
        self.assertEqual(resultat["compteurs"]["sinistres"], 3)
        self.assertIn("garanties", resultat["tables"])
        self.assertEqual(len(apercu()["apercu_sinistres"]), 3)

    def test_synchronisation_importe_polices_et_sinistres(self):
        resultat = synchroniser(self.session)
        self.assertEqual(resultat["polices_creees"], 4)
        self.assertEqual(resultat["sinistres_crees"], 3)
        self.assertEqual(len(self.session.exec(select(Police)).all()), 4)
        dossiers = self.session.exec(select(Dossier)).all()
        self.assertEqual(len(dossiers), 3)
        self.assertTrue(all(dossier.etat == "recu" for dossier in dossiers))
        self.assertTrue(all(dossier.montant_recommande is None for dossier in dossiers))
        self.assertTrue(all(dossier.montant_valide is None for dossier in dossiers))
        self.assertTrue(any(dossier.pieces for dossier in dossiers))
        evenement = self.session.exec(
            select(EvenementAudit).where(
                EvenementAudit.type == "synchronisation_donnees"
            )
        ).first()
        self.assertIsNotNone(evenement)

    def test_synchronisation_est_idempotente(self):
        synchroniser(self.session)
        resultat = synchroniser(self.session)
        self.assertEqual(resultat["polices_creees"], 0)
        self.assertEqual(resultat["polices_inchangees"], 4)
        self.assertEqual(resultat["sinistres_crees"], 0)
        self.assertEqual(resultat["sinistres_ignores"], 3)
        self.assertEqual(len(self.session.exec(select(Police)).all()), 4)
        self.assertEqual(len(self.session.exec(select(Dossier)).all()), 3)


if __name__ == "__main__":
    unittest.main()
