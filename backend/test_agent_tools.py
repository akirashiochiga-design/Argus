"""Tests unitaires des frontières de sécurité des agents outillés."""
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import llm
from app.agents import gravite, indemnite, runtime, tools
from app.models import Agent, Dossier, Police


class FauxBlocOutil:
    type = "tool_use"

    def __init__(self, identifiant="outil-1", nom="consulter_police"):
        self.id = identifiant
        self.name = nom
        self.input = {}

    def model_dump(self, exclude_none=True):
        return {
            "type": "tool_use",
            "id": self.id,
            "name": self.name,
            "input": self.input,
        }


class FauxBlocTexte:
    type = "text"

    def __init__(self, donnees):
        self.text = json.dumps(donnees)

    def model_dump(self, exclude_none=True):
        return {"type": "text", "text": self.text}


def fausse_reponse(*blocs):
    return SimpleNamespace(
        content=list(blocs),
        usage=SimpleNamespace(input_tokens=100, output_tokens=50),
    )


class AgentToolsTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        police = Police(
            numero="PA-TEST",
            assure_nom="Assuré Test",
            formule="tous_risques",
            garanties={"collision": {"plafond": 30000, "franchise": 220}},
            prime_payee=True,
            vehicule={
                "marque": "Volkswagen",
                "modele": "Golf 8",
                "immatriculation": "225 TU 4817",
                "annee": 2022,
            },
        )
        self.session.add(police)
        self.session.commit()
        self.session.refresh(police)
        self.dossier = Dossier(
            ref="SIN-TEST",
            police_id=police.id,
            declaration_texte="Choc avant droit sur le pare-chocs et le phare.",
            pieces=[{"type": "photo_degats", "chemin": "photo.jpg"}],
        )

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_outils_financiers_absents_des_listes_blanches(self):
        exposes = {
            nom
            for categorie in tools.OUTILS_PAR_CATEGORIE
            for nom in tools.noms_pour(categorie)
        }
        self.assertTrue(exposes.isdisjoint(tools.OUTILS_FINANCIERS_INTERDITS))

    def test_agent_vision_peut_consulter_le_vehicule(self):
        resultat = tools.executer_outil(
            "vision", "consulter_vehicule_assure", {}, self.dossier, self.session
        )
        self.assertEqual(resultat["modele"], "Golf 8")
        self.assertEqual(resultat["immatriculation"], "225 TU 4817")

    def test_outil_financier_est_refuse(self):
        with self.assertRaises(tools.OutilInterdit):
            tools.executer_outil(
                "fnol", "calculer_indemnite", {}, self.dossier, self.session
            )

    def test_identite_visuelle_reste_indeterminable_en_repli(self):
        agent = Agent(
            nom="Contrôle cohérence",
            categorie="vision",
            instructions="Vérifier la cohérence entre les photos et la déclaration.",
            garde_fous={"mission": "coherence"},
        )
        resultat = gravite._fallback(agent, self.dossier)
        self.assertEqual(
            resultat["verification_vehicule"]["statut"], "indeterminable"
        )

    def test_analyse_gravite_ne_contient_pas_de_controle_coherence(self):
        agent = Agent(
            nom="Analyse des dégâts",
            categorie="vision",
            instructions="Évaluer uniquement la gravité des dégâts.",
            garde_fous={"mission": "gravite"},
        )
        resultat = gravite._fallback(agent, self.dossier)
        self.assertEqual(resultat["classe"], "moyen")
        self.assertNotIn("coherence_declaration", resultat)
        self.assertNotIn("verification_vehicule", resultat)

    def test_calcul_financier_reste_determine_par_le_code(self):
        self.dossier.montant_estime = 2300.0
        self.dossier.position_couverture = {
            "couvert": True,
            "garantie": "collision",
            "franchise": 220,
            "plafond": 30000,
        }
        agent = Agent(
            nom="Calcul",
            categorie="indemnite",
            garde_fous={
                "bareme_vetuste": [
                    {"age_max": 2, "taux": 0.0},
                    {"age_max": 5, "taux": 0.1},
                    {"age_max": 99, "taux": 0.3},
                ]
            },
        )
        resultat = indemnite.executer(agent, self.dossier, self.session)
        self.assertEqual(resultat["montant_recommande"], 1850.0)
        self.assertEqual(resultat["mode"], "deterministe")

    def test_boucle_anthropic_execute_un_outil_puis_finalise(self):
        client = MagicMock()
        client.messages.create.side_effect = [
            fausse_reponse(FauxBlocOutil()),
            fausse_reponse(FauxBlocTexte({"statut": "ok"})),
        ]
        handler = MagicMock(return_value={"numero": "PA-TEST"})
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}), patch(
            "anthropic.Anthropic", return_value=client
        ):
            resultat = llm.generer_json_avec_outils(
                system="Agent test",
                texte_utilisateur="Consulte la police.",
                schema={
                    "type": "object",
                    "properties": {"statut": {"type": "string"}},
                    "required": ["statut"],
                    "additionalProperties": False,
                },
                outils=[tools.DEFINITIONS["consulter_police"]],
                executer_outil=handler,
            )

        self.assertEqual(resultat["donnees"], {"statut": "ok"})
        self.assertEqual(resultat["mode"], "agent_outille")
        self.assertEqual(resultat["iterations"], 2)
        self.assertEqual(resultat["actions"][0]["outil"], "consulter_police")
        handler.assert_called_once_with("consulter_police", {})
        self.assertEqual(
            client.messages.create.call_args_list[0].kwargs["tool_choice"],
            {"type": "any"},
        )
        self.assertEqual(
            client.messages.create.call_args_list[1].kwargs["tool_choice"],
            {"type": "auto"},
        )

    def test_boucle_agent_est_bornee(self):
        client = MagicMock()
        client.messages.create.side_effect = [
            fausse_reponse(FauxBlocOutil("outil-1")),
            fausse_reponse(FauxBlocOutil("outil-2")),
        ]
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}), patch(
            "anthropic.Anthropic", return_value=client
        ):
            with self.assertRaises(llm.LLMIndisponible):
                llm.generer_json_avec_outils(
                    system="Agent test",
                    texte_utilisateur="Boucle.",
                    schema={"type": "object"},
                    outils=[tools.DEFINITIONS["consulter_police"]],
                    executer_outil=lambda nom, entree: {"ok": True},
                    max_iterations=2,
                )

    def test_boucle_gemini_execute_un_outil_puis_finalise(self):
        client = MagicMock()
        usage = SimpleNamespace(prompt_token_count=100, candidates_token_count=50)
        client.models.generate_content.side_effect = [
            SimpleNamespace(
                function_calls=[
                    SimpleNamespace(name="consulter_police", args={})
                ],
                usage_metadata=usage,
            ),
            SimpleNamespace(
                text=json.dumps({"statut": "ok"}),
                usage_metadata=usage,
            ),
        ]
        handler = MagicMock(return_value={"numero": "PA-TEST"})
        environnement = {
            "GEMINI_API_KEY": "test",
            "LLM_PROVIDER": "gemini",
        }
        with patch.dict(os.environ, environnement), patch.object(
            llm, "_client_gemini", return_value=client
        ):
            resultat = llm.generer_json_avec_outils(
                system="Agent test",
                texte_utilisateur="Consulte la police.",
                schema={
                    "type": "object",
                    "properties": {"statut": {"type": "string"}},
                    "required": ["statut"],
                    "additionalProperties": False,
                },
                outils=[tools.DEFINITIONS["consulter_police"]],
                executer_outil=handler,
            )

        self.assertEqual(resultat["donnees"], {"statut": "ok"})
        self.assertEqual(resultat["iterations"], 2)
        self.assertEqual(resultat["actions"][0]["outil"], "consulter_police")
        handler.assert_called_once_with("consulter_police", {})
        self.assertEqual(client.models.generate_content.call_count, 2)

    def test_trace_repli_ne_divulgue_pas_erreur_api(self):
        trace = runtime.trace_repli(
            "fnol",
            "Structurer",
            "erreur API 400 : credit balance is too low, request_id=secret",
        )
        motif = trace["actions"][0]["resultat"]["motif"]
        self.assertNotIn("credit", motif.lower())
        self.assertNotIn("request_id", motif.lower())


if __name__ == "__main__":
    unittest.main()
