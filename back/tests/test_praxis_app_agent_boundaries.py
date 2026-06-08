import importlib
import pathlib
import unittest
from unittest.mock import Mock, patch


class PraxisAgentBoundaryTests(unittest.TestCase):
    def test_supervisor_registers_expected_team_subagents(self):
        supervisor = importlib.import_module("praxis_app.supervisor")

        with patch.object(supervisor, "create_deep_agent") as create_deep_agent, \
            patch.object(supervisor, "build_learning_agent", return_value=Mock(name="learning_agent")), \
            patch.object(
                supervisor,
                "build_learning_subagent",
                return_value={"name": "learning", "tools": []},
            ), \
            patch.object(
                supervisor,
                "build_career_subagent",
                return_value={"name": "access_career", "tools": []},
            ), \
            patch.object(
                supervisor,
                "build_resources_subagent",
                return_value={"name": "access_fyndr", "tools": []},
            ):
            supervisor.build_praxis_supervisor(
                name="praxis-supervisor",
                learning_name="learning",
                routing_model=Mock(),
                learning_model=Mock(),
                career_model=Mock(),
                assessment_team=Mock(),
                coaching_team=Mock(),
                session_manager=Mock(),
                gamification_engine=Mock(),
                navigate_to_page=Mock(),
                resource_tools=[Mock()],
                safe_middleware_factory=Mock(return_value=Mock()),
                checkpointer=Mock(),
                backend_factory=Mock(),
            )

        kwargs = create_deep_agent.call_args.kwargs
        self.assertEqual(kwargs["name"], "praxis-supervisor")
        self.assertEqual(
            [subagent["name"] for subagent in kwargs["subagents"]],
            ["learning", "access_career", "access_fyndr"],
        )

    def test_main_imports_praxis_supervisor_builder(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        main_source = (root / "main.py").read_text()

        self.assertIn("from praxis_app import build_praxis_supervisor", main_source)
        self.assertIn("supervisor_graph = build_praxis_supervisor(", main_source)
        self.assertNotIn("def build_supervisor_graph", main_source)


if __name__ == "__main__":
    unittest.main()
