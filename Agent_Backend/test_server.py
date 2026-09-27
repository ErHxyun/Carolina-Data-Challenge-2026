import json
import unittest
from unittest.mock import patch
import server

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        retrieval = patch.object(server, "collect_sources", return_value=([
            {"id": "web-1", "url": "https://ilo.org/report", "title": "ILO context", "excerpt": "Country context"}
        ], []))
        retrieval.start()
        self.addCleanup(retrieval.stop)

    def test_country_and_time_change(self):
        route = server.route_query("Explain time tax changes over time in Armenia")
        self.assertEqual((route["country_iso3"], route["topic"]), ("ARM", "time_changes"))
        self.assertIn("Armenia", route["question"])

    def test_us_pronoun_not_country(self):
        self.assertEqual(server.route_query("Tell us about China opportunity gap")["country_iso3"], "CHN")

    def test_chinese(self):
        self.assertEqual(server.route_query("中国的基础设施")["dimension"], "Infrastructure")

    def test_ambiguous_countries(self):
        with self.assertRaises(ValueError):
            server.route_query("Compare China and India")

    def test_invalid_country_and_path(self):
        with self.assertRaises(ValueError):
            server.validate_route({"country_iso3": "../../secrets"})

    def test_armenia_export_values(self):
        data = server.statistical_data(server.route_query("Freed time in Armenia"))
        row = data["facts"][0]["rows"][0]
        self.assertAlmostEqual(row["freed_minutes_per_day"], 34.12008, places=3)
        self.assertAlmostEqual(row["delta_female_lfpr_pp"], -0.558, places=3)
        self.assertIn("survey_comparability", row)

    def test_missing_year_not_substituted(self):
        data = server.statistical_data(server.route_query("Time tax Armenia 2024"))
        self.assertEqual(data["facts"][0]["rows"], [])
        self.assertTrue(data["warnings"])

    def test_delay_reference_year(self):
        data = server.statistical_data(server.route_query("Employment delay Armenia 2024"))
        self.assertIsNone(data["facts"][0]["delay"])
        self.assertTrue(data["warnings"])
        data = server.statistical_data(server.route_query("Employment delay Armenia 2021"))
        self.assertTrue(data["facts"][0]["delay"]["is_lower_bound"])

    def test_no_services_still_returns_data(self):
        with patch.object(server, "completion", side_effect=RuntimeError("offline")):
            report = server.build_report(server.route_query("Time tax Armenia"))
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["research"]["status"], "unavailable")
        self.assertTrue(report["statistics"]["data"]["facts"][0]["rows"])

    def test_uncited_research_not_used(self):
        with patch.object(server, "completion", return_value={"content": "Invented context", "annotations": []}):
            research = server.research_agent({}, {})
        self.assertEqual(research["status"], "unavailable")
        self.assertNotIn("Invented", research["summary"])

    def test_context_rejects_invented_reference(self):
        message = {"content": json.dumps({"claims": [{"text": "Context", "evidence_ids": ["invented"]}]})}
        with patch.object(server, "completion", return_value=message):
            research = server.research_agent({}, {})
        self.assertEqual(research["status"], "unavailable")

    def test_report_rejects_invented_reference(self):
        def mock_completion(system, payload, role, search=False):
            if role == "statistical":
                return {"content": '{"summary":"Local findings"}'}
            if role == "research":
                return {"content": json.dumps({"claims": [{"text": "Context", "evidence_ids": ["web-1"]}]})}
            return {"content": json.dumps({"sections": [{"title": "Bad", "text": "Claim", "evidence_ids": ["invented"]}]})}
        with patch.object(server, "completion", side_effect=mock_completion):
            report = server.build_report(server.route_query("Time tax Armenia"))
        self.assertEqual(report["status"], "partial")


    def test_complete_workflow(self):
        def mocked(system, payload, role, search=False):
            if role == "statistical":
                return {"content": '{"summary":"National time-use records are present."}'}
            if role == "research":
                return {"content": json.dumps({"claims": [{"text": "Country context", "evidence_ids": ["web-1"]}]})}
            return {"content": json.dumps({"sections": [{"title": "Findings", "text": "Read the national time-use records with country context.", "evidence_ids": ["local-analysis", "web-1"]}]})}
        with patch.object(server, "completion", side_effect=mocked):
            result = server.build_report(server.route_query("Time tax Armenia"))
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["research"]["sources"][0]["id"], "web-1")

    def test_chinese_year(self):
        self.assertEqual(server.route_query("中国2021年的基础设施")["year"], 2021)

if __name__ == "__main__":
    unittest.main()
