import unittest
from unittest.mock import patch

import brain.runtime_core as runtime_core
from tools import action_intelligence


class ActionIntelligenceTests(unittest.TestCase):
    def test_build_action_plan_decomposes_open_and_search(self):
        plan = action_intelligence.build_action_plan("open chrome and search AI trends")

        self.assertIsNotNone(plan)
        self.assertEqual([step.action_type for step in plan.steps], ["desktop_open", "browser_search"])
        self.assertEqual(plan.steps[0].target, "chrome")
        self.assertEqual(plan.steps[1].target, "AI trends")

    def test_build_action_plan_rejects_unsupported_steps(self):
        plan = action_intelligence.build_action_plan("open chrome and run powershell")

        self.assertIsNone(plan)

    def test_execute_action_plan_runs_steps_sequentially(self):
        plan = action_intelligence.build_action_plan("open chrome and search AI trends")
        self.assertIsNotNone(plan)

        with patch.object(
            action_intelligence,
            "open_application",
            return_value={"success": True, "status": "opened", "message": "Opening Chrome."},
        ) as open_mock, patch.object(
            action_intelligence,
            "open_chrome_search",
            return_value={"success": True, "status": "searched", "message": "Searching for AI trends."},
        ) as search_mock:
            result = action_intelligence.execute_action_plan(plan)

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["completed_steps"], 2)
        self.assertEqual(result["feedback"], ["Opening Chrome...", "Searching for AI trends..."])
        open_mock.assert_called_once_with("chrome")
        search_mock.assert_called_once_with("AI trends")

    def test_execute_action_plan_stops_on_failure(self):
        plan = action_intelligence.build_action_plan("open chrome and search AI trends")
        self.assertIsNotNone(plan)

        with patch.object(
            action_intelligence,
            "open_application",
            return_value={"success": False, "status": "unavailable", "message": "I couldn't find Chrome on this system."},
        ), patch.object(action_intelligence, "open_chrome_search") as search_mock:
            result = action_intelligence.execute_action_plan(plan)

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["completed_steps"], 0)
        self.assertEqual(result["failed_step"]["action_type"], "desktop_open")
        search_mock.assert_not_called()

    def test_runtime_routes_multi_step_action_plan_before_generic_multi_command(self):
        plan = action_intelligence.build_action_plan("open chrome and search AI trends")
        self.assertIsNotNone(plan)

        with patch.object(runtime_core, "build_action_plan", return_value=plan), patch.object(
            runtime_core,
            "execute_action_plan",
            return_value={
                "success": True,
                "status": "completed",
                "completed_steps": 2,
                "total_steps": 2,
                "failed_step": None,
                "feedback": ["Opening Chrome...", "Searching for AI trends..."],
                "plan": plan.to_dict(),
            },
        ), patch.object(
            runtime_core,
            "store_and_learn",
        ):
            result = runtime_core.process_command_detailed("open chrome and search AI trends", session_id="action-session")

        self.assertEqual(result["detected_intent"], "action_plan")
        self.assertEqual(result["execution_mode"], "action_plan")
        self.assertTrue(result["action_success"])
        self.assertEqual(result["action_steps"][1]["action_type"], "browser_search")
        self.assertIn("Opening Chrome", result["response"])


if __name__ == "__main__":
    unittest.main()
