import os
import unittest
from unittest.mock import patch
import tavily_research as tavily
import server


class TavilyTests(unittest.TestCase):
    route = {"country_name": "Armenia", "topic": "time_tax", "question": "Explain unpaid work", "year": 2021}

    def test_missing_key_never_calls_network(self):
        with patch.dict(os.environ, {"TAVILY_API_KEY": ""}), patch.object(tavily, "urlopen") as network:
            with self.assertRaises(tavily.ResearchUnavailable):
                tavily.collect_sources(self.route)
            network.assert_not_called()

    def test_extract_only_returned_urls_deduplicate_and_ignore_injected_urls(self):
        urls = ["https://ilo.org/a", "https://ilo.org/a#section", "javascript:alert(1)"]
        search = {"results": [{"url": url, "title": "ILO", "content": "Search snippet"} for url in urls]}
        extracted = {"results": [{"url": "https://ilo.org/a", "raw_content": "Extracted original text"},
                                 {"url": "https://other.org/fake", "raw_content": "Unrequested"}]}
        with patch.object(tavily, "request", side_effect=[search, search, extracted]) as api:
            sources, warnings = tavily.collect_sources(self.route)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["excerpt"], "Extracted original text")
        self.assertEqual(api.call_args.args[1]["urls"], ["https://ilo.org/a"])
        self.assertEqual(sources[0]["id"], "web-1")

    def test_extraction_failure_does_not_promote_snippets(self):
        search = {"results": [{"url": "https://ilo.org/a", "content": "Snippet"}]}
        with patch.object(tavily, "request", side_effect=[search, search, TimeoutError()]):
            sources, warnings = tavily.collect_sources(self.route)
        self.assertEqual(sources, [])
        self.assertTrue(warnings)

    def test_failed_search_retains_successful_search(self):
        search = {"results": [{"url": "https://ilo.org/a"}]}
        extracted = {"results": [{"url": "https://ilo.org/a", "raw_content": "Original"}]}
        with patch.object(tavily, "request", side_effect=[TimeoutError(), search, extracted]):
            sources, warnings = tavily.collect_sources(self.route)
        self.assertEqual(len(sources), 1)
        self.assertTrue(warnings)

    def test_missing_key_returns_actionable_limited_result(self):
        with patch.dict(os.environ, {"TAVILY_API_KEY": ""}), patch.object(server, "completion") as model:
            result = server.research_agent(self.route, {})
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("TAVILY_API_KEY", result["summary"])
        model.assert_not_called()


if __name__ == "__main__":
    unittest.main()
