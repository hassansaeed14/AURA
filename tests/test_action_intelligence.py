import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import brain.runtime_core as runtime_core
import tools.action_memory as action_memory
from tools import action_intelligence


class ActionIntelligenceTests(unittest.TestCase):
    def test_build_action_plan_decomposes_open_and_search(self):
        plan = action_intelligence.build_action_plan("open chrome and search AI trends")

        self.assertIsNotNone(plan)
        self.assertEqual([step.action_type for step in plan.steps], ["desktop_open", "browser_search"])
        self.assertEqual(plan.steps[0].target, "chrome")
        self.assertEqual(plan.steps[1].target, "AI trends")

    def test_safe_external_search_is_not_critical(self):
        classification = action_intelligence.classify_external_command_safety("open YouTube and search carryminati")
        plan = action_intelligence.build_action_plan("open YouTube and search carryminati")

        self.assertEqual(classification["trust_level"], "safe")
        self.assertIsNotNone(plan)
        self.assertEqual([step.action_type for step in plan.steps], ["browser_open_url", "browser_search"])
        self.assertEqual(plan.steps[0].target, "https://www.youtube.com/")
        self.assertEqual(plan.steps[1].target, "carryminati")

    def test_third_party_typing_is_sensitive_not_critical(self):
        classification = action_intelligence.classify_external_command_safety(
            "open ChatGPT and ask it to write an assignment"
        )
        plan = action_intelligence.build_action_plan("open ChatGPT and ask it to write an assignment")

        self.assertEqual(classification["trust_level"], "sensitive")
        self.assertIsNotNone(plan)
        self.assertEqual(
            [step.action_type for step in plan.steps],
            ["browser_open_url", "automation_confirm", "automation_type"],
        )
        self.assertEqual(plan.steps[2].target, "chrome")
        self.assertEqual(plan.steps[2].params["trust_level"], "sensitive")

    def test_password_payment_banking_and_delete_are_critical(self):
        samples = [
            "type my password",
            "open chrome and pay the bill",
            "type bank details in notepad",
            "delete files",
        ]

        for sample in samples:
            with self.subTest(sample=sample):
                classification = action_intelligence.classify_external_command_safety(sample)
                plan = action_intelligence.build_action_plan(sample)
                self.assertEqual(classification["trust_level"], "critical")
                self.assertIsNotNone(plan)
                self.assertTrue(any(step.action_type == "automation_critical_blocked" for step in plan.steps))

    def test_build_action_plan_decomposes_open_and_go_to_url(self):
        plan = action_intelligence.build_action_plan("open chrome and go to example.com")

        self.assertIsNotNone(plan)
        self.assertEqual([step.action_type for step in plan.steps], ["desktop_open", "browser_navigate_url"])
        self.assertEqual(plan.steps[1].target, "example.com")

    def test_build_action_plan_hydrates_open_top_link_from_previous_search(self):
        plan = action_intelligence.build_action_plan("search AI trends and open top link")

        self.assertIsNotNone(plan)
        self.assertEqual([step.action_type for step in plan.steps], ["browser_search", "browser_open_result"])
        self.assertEqual(plan.steps[1].target, "AI trends")

    def test_build_action_plan_supports_single_open_first_result_with_query(self):
        plan = action_intelligence.build_action_plan("open first result for Python docs")

        self.assertIsNotNone(plan)
        self.assertEqual([step.action_type for step in plan.steps], ["browser_open_result"])
        self.assertEqual(plan.steps[0].target, "Python docs")

    def test_build_action_plan_supports_phase_7_browser_actions(self):
        plan = action_intelligence.build_action_plan("open chrome and open new tab and navigate to example.com")

        self.assertIsNotNone(plan)
        self.assertEqual(
            [step.action_type for step in plan.steps],
            ["desktop_open", "browser_new_tab", "browser_navigate_url"],
        )

    def test_build_action_plan_hydrates_rerun_and_next_result(self):
        plan = action_intelligence.build_action_plan("search AI trends and rerun search and open next result")

        self.assertIsNotNone(plan)
        self.assertEqual(
            [step.action_type for step in plan.steps],
            ["browser_search", "browser_rerun_search", "browser_open_result"],
        )
        self.assertEqual(plan.steps[1].target, "AI trends")
        self.assertEqual(plan.steps[2].target, "AI trends")
        self.assertEqual(plan.steps[2].params["result_index"], 2)

    def test_build_action_plan_inserts_confirmation_before_typing(self):
        plan = action_intelligence.build_action_plan("open notepad and type hello")

        self.assertIsNotNone(plan)
        self.assertEqual(
            [step.action_type for step in plan.steps],
            ["desktop_open", "automation_confirm", "automation_type"],
        )
        self.assertEqual(plan.steps[2].target, "notepad")
        self.assertTrue(plan.steps[1].params["requires_confirmation"])

    def test_build_action_plan_rejects_unsupported_steps(self):
        plan = action_intelligence.build_action_plan("open chrome and run powershell")

        self.assertIsNone(plan)

    def test_execute_action_plan_runs_steps_sequentially(self):
        plan = action_intelligence.build_action_plan("open chrome and search AI trends")
        self.assertIsNotNone(plan)

        with TemporaryDirectory() as root, patch.object(action_memory, "ACTION_MEMORY_FILE", Path(root) / "action_memory.json"):
            with patch.object(
                action_intelligence,
                "open_application",
                return_value={"success": True, "status": "opened", "message": "Opening Chrome."},
            ) as open_mock, patch.object(
                action_intelligence,
                "search_query",
                return_value={"success": True, "verified": True, "status": "searched", "url": "https://www.google.com/search?q=AI+trends", "message": "Searching for AI trends."},
            ) as search_mock:
                result = action_intelligence.execute_action_plan(plan)

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["completed_steps"], 2)
        self.assertEqual(result["plan"]["steps"][0]["status"], "success")
        self.assertEqual(result["feedback"], ["Opening Chrome...", "Searching for AI trends..."])
        open_mock.assert_called_once_with("chrome")
        search_mock.assert_called_once_with("AI trends")

    def test_execute_action_plan_stops_on_failure(self):
        plan = action_intelligence.build_action_plan("open chrome and search AI trends")
        self.assertIsNotNone(plan)

        with TemporaryDirectory() as root, patch.object(action_memory, "ACTION_MEMORY_FILE", Path(root) / "action_memory.json"):
            with patch.object(
                action_intelligence,
                "open_application",
                return_value={"success": False, "status": "unavailable", "message": "I couldn't find Chrome on this system."},
            ), patch.object(action_intelligence, "search_query") as search_mock:
                result = action_intelligence.execute_action_plan(plan)

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["completed_steps"], 0)
        self.assertEqual(result["failed_step"]["action_type"], "desktop_open")
        search_mock.assert_not_called()

    def test_execute_action_plan_retries_unverified_browser_step_once(self):
        plan = action_intelligence.build_action_plan("search AI trends and open top link")
        self.assertIsNotNone(plan)

        with TemporaryDirectory() as root, patch.object(action_memory, "ACTION_MEMORY_FILE", Path(root) / "action_memory.json"):
            with patch.object(
                action_intelligence,
                "search_query",
                side_effect=[
                    {"success": True, "verified": False, "status": "searched", "message": "Searching for AI trends."},
                    {"success": True, "verified": True, "status": "searched", "url": "https://www.google.com/search?q=AI+trends", "message": "Searching for AI trends."},
                ],
            ) as search_mock, patch.object(
                action_intelligence,
                "open_search_result",
                return_value={
                    "success": True,
                    "verified": True,
                    "status": "top_result_requested",
                    "url": "https://www.google.com/search?q=AI+trends&btnI=I",
                    "message": "Opening the top result for AI trends.",
                },
            ):
                result = action_intelligence.execute_action_plan(plan)

        self.assertTrue(result["success"])
        self.assertEqual(search_mock.call_count, 2)
        self.assertEqual(result["plan"]["steps"][0]["result"]["attempts"], 2)

    def test_execute_action_plan_recovers_result_failure_to_search_page(self):
        plan = action_intelligence.build_action_plan("open first result for Python docs")
        self.assertIsNotNone(plan)

        with TemporaryDirectory() as root, patch.object(action_memory, "ACTION_MEMORY_FILE", Path(root) / "action_memory.json"):
            with patch.object(
                action_intelligence,
                "open_search_result",
                return_value={"success": False, "verified": False, "status": "launch_failed", "message": "Top result failed."},
            ), patch.object(
                action_intelligence,
                "search_query",
                return_value={
                    "success": True,
                    "verified": True,
                    "status": "searched",
                    "url": "https://www.google.com/search?q=Python+docs",
                    "message": "Searching for Python docs.",
                    "query": "Python docs",
                },
            ):
                result = action_intelligence.execute_action_plan(plan)

        self.assertTrue(result["success"])
        self.assertTrue(result["plan"]["steps"][0]["result"]["recovered"])
        self.assertIn("safe Google search page", result["feedback"][-1])

    def test_execute_action_plan_requires_confirmation_before_control(self):
        plan = action_intelligence.build_action_plan("open notepad and type hello")
        self.assertIsNotNone(plan)

        with TemporaryDirectory() as root, patch.object(action_memory, "ACTION_MEMORY_FILE", Path(root) / "action_memory.json"):
            with patch.object(
                action_intelligence,
                "open_application",
                return_value={"success": True, "status": "opened", "message": "Opening Notepad."},
            ), patch.object(action_intelligence, "type_text") as type_mock:
                result = action_intelligence.execute_action_plan(plan)

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "needs_confirmation")
        self.assertTrue(result["automation_confirmation_required"])
        self.assertEqual(result["failed_step"]["action_type"], "automation_confirm")
        type_mock.assert_not_called()

    def test_execute_action_plan_runs_control_after_confirmation(self):
        plan = action_intelligence.build_action_plan("open notepad and type hello")
        self.assertIsNotNone(plan)

        with TemporaryDirectory() as root, patch.object(action_memory, "ACTION_MEMORY_FILE", Path(root) / "action_memory.json"):
            with patch.object(
                action_intelligence,
                "open_application",
                return_value={"success": True, "status": "opened", "message": "Opening Notepad."},
            ), patch.object(
                action_intelligence,
                "type_text",
                return_value={"success": True, "status": "typed", "message": "Typed text into Notepad."},
            ) as type_mock:
                result = action_intelligence.execute_action_plan(plan, automation_confirmed=True)

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["automation_confirmation_required"])
        type_mock.assert_called_once_with("hello", "notepad")

    def test_control_step_runs_once_even_when_it_fails(self):
        plan = action_intelligence.build_action_plan("open notepad and type hello")
        self.assertIsNotNone(plan)

        with TemporaryDirectory() as root, patch.object(action_memory, "ACTION_MEMORY_FILE", Path(root) / "action_memory.json"):
            with patch.object(
                action_intelligence,
                "open_application",
                return_value={"success": True, "status": "opened", "message": "Opening Notepad."},
            ), patch.object(
                action_intelligence,
                "type_text",
                return_value={"success": False, "status": "stopped", "message": "Control stopped."},
            ) as type_mock:
                result = action_intelligence.execute_action_plan(plan, automation_confirmed=True)

        self.assertFalse(result["success"])
        self.assertEqual(type_mock.call_count, 1)
        self.assertEqual(result["failed_step"]["result"]["attempts"], 1)
        self.assertTrue(result["failed_step"]["result"]["single_execution"])

    def test_control_plan_uses_small_cooldown_between_steps(self):
        plan = action_intelligence.build_action_plan("open notepad and type hello")
        self.assertIsNotNone(plan)

        with TemporaryDirectory() as root, patch.object(action_memory, "ACTION_MEMORY_FILE", Path(root) / "action_memory.json"):
            with patch.object(
                action_intelligence,
                "open_application",
                return_value={"success": True, "status": "opened", "message": "Opening Notepad."},
            ), patch.object(
                action_intelligence,
                "type_text",
                return_value={"success": True, "status": "typed", "message": "Typed text into Notepad."},
            ), patch.object(action_intelligence.time, "sleep") as sleep_mock:
                result = action_intelligence.execute_action_plan(plan, automation_confirmed=True)

        self.assertTrue(result["success"])
        self.assertGreaterEqual(sleep_mock.call_count, 2)
        sleep_mock.assert_any_call(action_intelligence.ACTION_STEP_COOLDOWN_SECONDS)

    def test_execute_action_plan_blocks_critical_automation(self):
        plan = action_intelligence.build_action_plan("open notepad and type my password is secret")
        self.assertIsNotNone(plan)

        with TemporaryDirectory() as root, patch.object(action_memory, "ACTION_MEMORY_FILE", Path(root) / "action_memory.json"):
            with patch.object(
                action_intelligence,
                "open_application",
                return_value={"success": True, "status": "opened", "message": "Opening Notepad."},
            ):
                result = action_intelligence.execute_action_plan(plan, automation_confirmed=True)

        self.assertFalse(result["success"])
        self.assertEqual(result["failed_step"]["action_type"], "automation_critical_blocked")
        self.assertEqual(result["failed_step"]["result"]["trust_level"], "critical")

    def test_critical_action_is_blocked_as_action_plan(self):
        plan = action_intelligence.build_action_plan("delete files")

        self.assertIsNotNone(plan)
        self.assertEqual(plan.steps[0].action_type, "automation_critical_blocked")

    def test_action_memory_records_repeated_search_suggestions(self):
        plan = action_intelligence.build_action_plan("search AI trends and open top link")
        self.assertIsNotNone(plan)

        with TemporaryDirectory() as root, patch.object(action_memory, "ACTION_MEMORY_FILE", Path(root) / "action_memory.json"):
            with patch.object(
                action_intelligence,
                "search_query",
                return_value={
                    "success": True,
                    "verified": True,
                    "status": "searched",
                    "url": "https://www.google.com/search?q=AI+trends",
                    "message": "Searching for AI trends.",
                    "query": "AI trends",
                },
            ), patch.object(
                action_intelligence,
                "open_search_result",
                return_value={
                    "success": True,
                    "verified": True,
                    "status": "top_result_requested",
                    "url": "https://www.google.com/search?q=AI+trends&btnI=I",
                    "message": "Opening the top result for AI trends.",
                    "query": "AI trends",
                },
            ):
                action_intelligence.execute_action_plan(plan)
                second = action_intelligence.execute_action_plan(action_intelligence.build_action_plan("search AI trends and open top link"))

        self.assertTrue(second["suggestions"])
        self.assertIn("AI trends", second["suggestions"][0]["text"])

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
