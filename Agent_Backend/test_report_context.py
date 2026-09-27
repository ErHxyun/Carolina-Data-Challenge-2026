import unittest
from copy import deepcopy
from unittest.mock import patch
import server

class ReportContextTests(unittest.TestCase):
    def test_reduction_preserves_cited_original_and_warnings(self):
        research={"status":"complete", "summary":"Repeated summary "*100,
                  "claims":[{"text":"Evidence", "evidence_ids":["web-1"]}],
                  "sources":[{"id":"web-1","excerpt":"Cited full text","published_date":"2025"},
                             {"id":"web-2","excerpt":"Unused text "*1000}],
                  "warnings":["Later context"]}
        before=deepcopy(research)
        result=server.report_context(research)
        self.assertEqual(result["sources"],[research["sources"][0]])
        self.assertEqual(result["claims"],research["claims"])
        self.assertEqual(result["warnings"],research["warnings"])
        self.assertNotIn("summary", result)
        self.assertEqual(research,before)
    def test_incomplete_or_invalid_claims_preserve_evidence(self):
        for claims in (None, [], [{"evidence_ids":["unknown"]}]):
            research={"status":"complete","claims":claims,"sources":[{"id":"web-1"}]}
            self.assertIs(server.report_context(research),research)
    def test_report_keeps_original_evidence_for_user(self):
        route=server.route_query("Explain time tax in Armenia")
        bundle=server.statistical_data(route)
        stat={"status":"complete","data":bundle,"summary":"Local results"}
        research={"status":"complete","summary":"Context", "claims":[{"text":"Context","evidence_ids":["web-1"]}],
                  "sources":[{"id":"web-1","excerpt":"Evidence"},{"id":"web-2","excerpt":"Other"}]}
        with patch.object(server,"completion",return_value={"content":'{"sections":[{"title":"Answer","text":"Context","evidence_ids":["web-1"]}]}'}) as call:
            report=server.report_agent(route,bundle,stat,research)
        payload=call.call_args.args[1]
        self.assertEqual(payload["statistics"]["data"],bundle)
        self.assertEqual(len(payload["research"]["sources"]),1)
        self.assertEqual(len(report["research"]["sources"]),2)
        self.assertEqual(report["status"],"complete")
