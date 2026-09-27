import threading
import unittest
from unittest.mock import Mock

from workflow import create_report_graph, run_report_graph


class GraphTests(unittest.TestCase):
    def test_parallel_branches_join_once_and_emit_early_completion(self):
        rendezvous = threading.Barrier(2)
        release_statistics = threading.Event()

        def statistics(bundle):
            rendezvous.wait(timeout=3)
            if not release_statistics.wait(3):
                raise RuntimeError("Research progress was buffered until join")
            return {"status": "complete", "data": bundle}

        def research(route, bundle):
            rendezvous.wait(timeout=3)
            return {"status": "unavailable", "sources": []}

        writer = Mock(return_value={"status": "partial"})
        graph = create_report_graph(lambda route: route, lambda route: {"iso": route["iso"]}, statistics, research, writer)
        events = []

        def progress(stage, status):
            events.append((stage, status))
            if (stage, status) == ("research", "limited"):
                release_statistics.set()

        result = run_report_graph(graph, {"iso": "ARM"}, progress)
        self.assertEqual(result["status"], "partial")
        writer.assert_called_once()
        self.assertEqual(writer.call_args.args[2]["data"], {"iso": "ARM"})
        report_start = events.index(("report", "running"))
        self.assertLess(events.index(("statistics", "complete")), report_start)
        self.assertLess(events.index(("research", "limited")), report_start)

    def test_reused_graph_does_not_leak_request_state(self):
        graph = create_report_graph(
            lambda route: route,
            lambda route: {"iso": route["iso"]},
            lambda bundle: {"status": "complete", "data": bundle},
            lambda route, bundle: {"status": "complete", "iso": route["iso"]},
            lambda route, bundle, stat, research: {"status": "complete", "iso": research["iso"], "data": stat["data"]},
        )
        for iso in ("ARM", "CHN"):
            report = run_report_graph(graph, {"iso": iso}, lambda *args: None)
            self.assertEqual(report["iso"], iso)
            self.assertEqual(report["data"], {"iso": iso})


if __name__ == "__main__":
    unittest.main()
