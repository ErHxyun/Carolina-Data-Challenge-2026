import json
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

import server


class PhaseTests(unittest.TestCase):
    def test_stream_delivers_progress_before_report_finishes(self):
        release = threading.Event()

        def statistics(bundle):
            if not release.wait(5):
                raise RuntimeError("Client did not receive progress")
            return {"status": "complete", "summary": "Local findings", "data": bundle}

        research = {"status": "complete", "summary": "Context", "sources": []}
        draft = {"content": json.dumps({"sections": [{"title": "Finding", "text": "Test report", "evidence_ids": ["local-analysis"]}]})}
        httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        with patch.object(server, "statistical_agent", side_effect=statistics), patch.object(server, "research_agent", return_value=research), patch.object(server, "completion", return_value=draft):
            thread.start()
            try:
                route = server.route_query("Time tax Armenia")
                req = Request(f"http://127.0.0.1:{httpd.server_port}/api/report/stream", data=json.dumps(route).encode(), headers={"Origin": "http://localhost:5173", "Content-Type": "application/json"})
                with urlopen(req, timeout=10) as response:
                    first = json.loads(response.readline())
                    self.assertEqual(first["type"], "phase")
                    self.assertIn(first["stage"], ("statistics", "research"))
                    self.assertEqual(first["status"], "running")
                    release.set()
                    events = [first] + [json.loads(line) for line in response]
                phases = [(e["stage"], e["status"]) for e in events if e["type"] == "phase"]
                writing = phases.index(("report", "running"))
                for stage in ("statistics", "research"):
                    self.assertLess(phases.index((stage, "complete")), writing)
                self.assertEqual(events[-1]["type"], "result")
                self.assertEqual(events[-1]["report"]["status"], "complete")
            finally:
                release.set()
                httpd.shutdown()
                httpd.server_close()
                thread.join()

    def test_unavailable_services_emit_limited_status(self):
        events = []
        with patch.object(server, "collect_sources", return_value=([], [])), patch.object(server, "completion", side_effect=RuntimeError("offline")):
            result = server.build_report(server.route_query("Time tax Armenia"), lambda *event: events.append(event))
        self.assertEqual(result["status"], "partial")
        for stage in ("statistics", "research", "report"):
            self.assertIn((stage, "limited"), events)
        self.assertEqual(events[-1], ("report", "limited"))


if __name__ == "__main__":
    unittest.main()
