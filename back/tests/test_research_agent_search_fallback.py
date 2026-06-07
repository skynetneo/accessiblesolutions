import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "teams" / "research" / "research_agent.py"


def load_research_agent_module():
    module_name = "research_agent_test_module"
    sys.modules.pop(module_name, None)

    graph_stub = types.ModuleType("graph")
    graph_stub.create_deep_agent = lambda *args, **kwargs: {"stub_agent": True}
    sys.modules["graph"] = graph_stub

    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InternetSearchFallbackTests(unittest.TestCase):
    def setUp(self):
        self.module = load_research_agent_module()

    def test_tavily_success_returns_provider_metadata(self):
        tavily_client = Mock()
        tavily_client.search.return_value = {
            "results": [{"title": "Fractions", "url": "https://example.com/fractions", "content": "Basics"}]
        }

        with (
            patch.object(self.module, "_get_tavily_client", return_value=(tavily_client, None)),
            patch.object(self.module, "_search_duckduckgo") as ddg_search,
        ):
            result = self.module.internet_search("fraction basics")

        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "tavily")
        self.assertFalse(result["fallback_used"])
        self.assertEqual(result["results"][0]["url"], "https://example.com/fractions")
        ddg_search.assert_not_called()

    def test_tavily_unavailable_falls_back_to_duckduckgo(self):
        fallback_results = [{"title": "Decimals", "url": "https://example.com/decimals", "content": "How to convert"}]
        fallback_raw = [{"title": "Decimals", "href": "https://example.com/decimals", "body": "How to convert"}]

        with (
            patch.object(self.module, "_get_tavily_client", return_value=(None, "Tavily unavailable: missing key")),
            patch.object(self.module, "_search_duckduckgo", return_value=(fallback_results, fallback_raw, None)),
        ):
            result = self.module.internet_search("decimal conversion")

        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "duckduckgo")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["raw"], fallback_raw)

    def test_tavily_runtime_failure_falls_back_to_duckduckgo(self):
        tavily_client = Mock()
        tavily_client.search.side_effect = RuntimeError("quota exhausted")
        fallback_results = [{"title": "Ratios", "url": "https://example.com/ratios", "content": "Examples"}]
        fallback_raw = [{"title": "Ratios", "href": "https://example.com/ratios", "body": "Examples"}]

        with (
            patch.object(self.module, "_get_tavily_client", return_value=(tavily_client, None)),
            patch.object(self.module, "_search_duckduckgo", return_value=(fallback_results, fallback_raw, None)),
        ):
            result = self.module.internet_search("ratio practice")

        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "duckduckgo")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["results"][0]["title"], "Ratios")

    def test_both_providers_failing_returns_combined_error_details(self):
        with (
            patch.object(self.module, "_get_tavily_client", return_value=(None, "Tavily unavailable: missing key")),
            patch.object(
                self.module,
                "_search_duckduckgo",
                return_value=(None, None, "DuckDuckGo unavailable: package not installed"),
            ),
        ):
            result = self.module.internet_search("long division")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "internet_search_failed")
        self.assertEqual(result["provider"], "none")
        self.assertTrue(result["fallback_used"])
        self.assertIn("Tavily unavailable: missing key", result["details"])
        self.assertIn("DuckDuckGo unavailable: package not installed", result["details"])

    def test_duckduckgo_normalization_matches_expected_result_shape(self):
        raw_results = [{"title": "Percentages", "href": "https://example.com/percent", "body": "Use ratios"}]

        normalized = self.module._normalize_duckduckgo_results(raw_results, include_raw_content=True)

        self.assertEqual(len(normalized), 1)
        self.assertEqual(normalized[0]["title"], "Percentages")
        self.assertEqual(normalized[0]["url"], "https://example.com/percent")
        self.assertEqual(normalized[0]["content"], "Use ratios")
        self.assertEqual(normalized[0]["raw_content"], "Use ratios")


if __name__ == "__main__":
    unittest.main()
