import importlib
import types
import unittest
from unittest.mock import Mock, patch


def load_employment_services_module():
    return importlib.import_module("teams.employment_services")


class EmploymentServicesToolTests(unittest.TestCase):
    def setUp(self):
        self.module = load_employment_services_module()
        self.runtime = types.SimpleNamespace(
            context=types.SimpleNamespace(learner_id="learner-123"),
            store=None,
            tool_call_id="tool-call-1",
        )

    def test_search_jobs_returns_legacy_compatible_mock_listing_text(self):
        result = self.module.search_jobs.func(
            "Data Analyst",
            "remote",
            55000,
            self.runtime,
            job_type="full_time",
        )

        self.assertIn("[MOCK API RESPONSE]", result)
        self.assertIn("Found 3 matching jobs for 'Data Analyst' in remote", result)
        self.assertIn("starting above $55000/yr", result)
        self.assertIn("Junior Data Analyst - ACME Corp - $60000/yr", result)
        self.assertIn("Associate Data Analyst - Globex - $57000/yr", result)
        self.assertIn("Data Analyst Coordinator - Initech - $65000/yr", result)

    def test_analyze_job_fit_returns_legacy_compatible_analysis_directive(self):
        result = self.module.analyze_job_fit.func(
            "Build dashboards and communicate operational insights.",
            "Operations Analyst",
            self.runtime,
        )

        self.assertIn("analyze the 'Operations Analyst' role", result)
        self.assertIn("Existing skill matches (%)", result)
        self.assertIn("Gaps (what's missing)", result)
        self.assertIn("Estimated time to close gap", result)
        self.assertIn("Bridge viability score (Pay Increase / Gap Size)", result)

    def test_save_job_research_persists_to_supabase_without_network(self):
        execute_result = types.SimpleNamespace(data={"id": "row-1"})
        insert_query = Mock()
        insert_query.execute.return_value = execute_result
        table_query = Mock()
        table_query.insert.return_value = insert_query
        client = Mock()
        client.table.return_value = table_query
        research_summary = {
            "roles": ["Operations Analyst"],
            "skill_gaps": ["SQL"],
            "recommended_actions": ["Finish SQL module"],
        }

        with patch.object(self.module, "db", types.SimpleNamespace(client=client)):
            result = self.module.save_job_research.func(research_summary, self.runtime)

        self.assertIn("Research saved successfully as research_", result)
        client.table.assert_called_once_with("job_research")
        payload = table_query.insert.call_args.args[0]
        self.assertEqual(payload["learner_id"], "learner-123")
        self.assertTrue(payload["research_id"].startswith("research_"))
        self.assertEqual(payload["research_summary"], research_summary)
        self.assertIn("created_at", payload)
        insert_query.execute.assert_called_once_with()

    def test_job_researcher_subagent_exposes_legacy_parity_tools(self):
        tools = self.module.job_researcher_subagent["tools"]

        self.assertIn(self.module.search_jobs, tools)
        self.assertIn(self.module.analyze_job_fit, tools)
        self.assertIn(self.module.save_job_research, tools)
        self.assertIn(
            "Always call save_job_research",
            self.module.job_researcher_subagent["system_prompt"],
        )


if __name__ == "__main__":
    unittest.main()
