"""Tests des parcours ajoutés pour la finale : Marketplace et adaptateurs."""
import unittest

from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.connectors.documents_local import ConnecteurDocumentsLocal
from app.connectors.erp_stub import ConnecteurERPDemo
from app.connectors.erp_tn import ConnecteurERPMarcheTN, SYSTEMES_ERP_TN, construire_tous
from app.connectors.insurance_sqlite import synchroniser
from app.connectors.registry import catalogue
from app.models import (
    Agent,
    Dossier,
    EcritureERP,
    EvenementAudit,
    MarketplaceInstallation,
    Police,
    Tache,
    Workflow,
)
from app.routers.marketplace import (
    SoumissionTemplate,
    installer_listing,
    lister_listings,
    lister_listings_editeur,
    soumettre_listing,
    valider_listing,
)
from app.routers.taches import Decision, decider_tache
from app.seed import build_marketplace


class ParcoursFinaleTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_achat_marketplace_cree_agent_live_une_seule_fois(self):
        listing = build_marketplace()[0]
        self.session.add(listing)
        self.session.commit()
        self.session.refresh(listing)

        resultat = installer_listing(listing.id, self.session)
        agent = resultat["agent"]
        self.assertEqual(agent.statut, "live")
        self.assertEqual(agent.garde_fous["origine"], "marketplace")
        self.assertFalse(resultat["deja_installe"])

        second = installer_listing(listing.id, self.session)
        self.assertTrue(second["deja_installe"])
        self.assertEqual(len(self.session.exec(select(Agent)).all()), 1)
        self.assertEqual(
            len(self.session.exec(select(MarketplaceInstallation)).all()),
            1,
        )

    def test_publication_template_refuse_les_secrets(self):
        with self.assertRaises(HTTPException) as contexte:
            soumettre_listing(
                SoumissionTemplate(
                    nom="Template risqué",
                    categorie="vision",
                    editeur="Freelance test",
                    description="Une description métier suffisamment longue pour le contrôle.",
                    instructions=(
                        "Analyse les photos avec api_key=demo-interdit et retourne "
                        "une synthèse structurée."
                    ),
                ),
                self.session,
            )
        self.assertEqual(contexte.exception.status_code, 422)

    def test_template_valide_devient_achetable(self):
        listing = soumettre_listing(
            SoumissionTemplate(
                nom="Synthèse expertise",
                categorie="courrier",
                editeur="Freelance test",
                description="Prépare une synthèse claire des conclusions de l'expert.",
                instructions=(
                    "Rédige une synthèse factuelle à partir des conclusions fournies, "
                    "sans inventer de montant ni prendre de décision."
                ),
                prix=120,
            ),
            self.session,
        )
        self.assertEqual(listing.statut, "en_attente")
        self.assertEqual(lister_listings(self.session), [])
        self.assertEqual(len(lister_listings_editeur("Freelance test", self.session)), 1)
        listing = valider_listing(listing.id, self.session)
        self.assertEqual(listing.statut, "publie")
        self.assertTrue(listing.verifie)
        self.assertEqual(len(lister_listings(self.session)), 1)

    def test_sharepoint_est_idempotent(self):
        self.session.add(Workflow(nom="Parcours test", statut="live", etapes=[]))
        self.session.commit()
        synchroniser(self.session)
        connecteur = ConnecteurDocumentsLocal()
        premier = connecteur.synchroniser(self.session)
        second = connecteur.synchroniser(self.session)
        self.assertEqual(premier["documents_importes"], 2)
        self.assertEqual(second["documents_importes"], 0)
        self.assertEqual(second["documents_ignores"], 2)

    def test_approbation_humaine_planifie_ecriture_erp_interne(self):
        police = Police(
            numero="TEST-ERP",
            assure_nom="Assuré test",
            formule="tous_risques",
        )
        self.session.add(police)
        self.session.flush()
        dossier = Dossier(
            ref="TEST-ERP-001",
            police_id=police.id,
            declaration_texte="Test",
            etat="attente_validation",
            montant_recommande=1850,
        )
        self.session.add(dossier)
        self.session.flush()
        tache = Tache(
            dossier_id=dossier.id,
            type="validation_reglement",
            montant=1850,
        )
        self.session.add(tache)
        self.session.commit()
        self.session.refresh(tache)

        resultat_decision = decider_tache(
            tache.id,
            Decision(decision="approuver", validateur="Zak Chammam"),
            self.session,
        )
        self.assertEqual(resultat_decision["ecriture_erp"]["statut"], "planifiee")
        resultat = ConnecteurERPDemo().synchroniser(self.session)
        self.assertEqual(resultat["ecritures_envoyees"], 1)
        ecriture = self.session.exec(select(EcritureERP)).one()
        self.assertEqual(ecriture.statut, "envoyee")
        evenements = self.session.exec(select(EvenementAudit)).all()
        self.assertTrue(
            {"ecriture_erp_planifiee", "ecriture_erp_envoyee"}.issubset(
                {event.type for event in evenements}
            )
        )

    def test_erp_marche_tn_dans_registre_et_sync_idempotente(self):
        ids = {item["identifiant"] for item in catalogue()}
        for definition in SYSTEMES_ERP_TN:
            self.assertIn(definition["identifiant"], ids)

        police = Police(numero="TEST-TN", assure_nom="Assuré TN", formule="tous_risques")
        self.session.add(police)
        self.session.flush()
        dossier = Dossier(
            ref="TEST-TN-001",
            police_id=police.id,
            declaration_texte="Test ERP TN",
            etat="regle",
            montant_valide=1850,
        )
        self.session.add(dossier)
        self.session.commit()

        digiclaim = next(c for c in construire_tous() if c.identifiant == "digiclaim")
        self.assertTrue(digiclaim.tester()["simulation"])
        premier = digiclaim.synchroniser(self.session)
        second = digiclaim.synchroniser(self.session)
        self.assertEqual(premier["dossiers_pushes"], 1)
        self.assertEqual(second["dossiers_pushes"], 0)
        self.assertEqual(second["dossiers_ignores"], 1)
        events = self.session.exec(
            select(EvenementAudit).where(
                EvenementAudit.type == "synchronisation_erp_marche"
            )
        ).all()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].apres["connecteur"], "digiclaim")
        self.assertIsInstance(digiclaim, ConnecteurERPMarcheTN)


if __name__ == "__main__":
    unittest.main()
