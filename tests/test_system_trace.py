import unittest

from brain.system_trace import build_action_trace, new_request_id


class SystemTraceTests(unittest.TestCase):
    def test_trace_marks_control_plan_pending_approval(self):
        trace = build_action_trace(
            request_id=new_request_id("test"),
            raw_input="open notepad and type hello",
            intent="action_plan",
            provider=None,
            permission={
                "success": True,
                "status": "approved",
                "permission": {
                    "action_name": "desktop_launch",
                    "trust_level": "safe",
                    "approval_type": "none",
                },
            },
            action_plan={
                "plan_id": "action-test",
                "status": "running",
                "steps": [
                    {"step_id": "step-1", "action_type": "desktop_open", "label": "Open Notepad", "status": "success"},
                    {"step_id": "step-2", "action_type": "automation_confirm", "label": "Confirm control", "status": "pending"},
                    {"step_id": "step-3", "action_type": "automation_type", "label": "Type text", "status": "pending"},
                ],
            },
            source={"automation_confirmation_required": True, "automation_control": True, "action_status": "needs_confirmation"},
            success=True,
            status="needs_confirmation",
        )

        self.assertEqual(trace["response_mode"], "control_pending")
        self.assertEqual(trace["final_status"], "pending_approval")
        self.assertTrue(trace["automation_state"]["active"])
        self.assertTrue(trace["automation_state"]["confirmation_required"])
        self.assertEqual(trace["action_plan"]["step_count"], 3)

    def test_trace_marks_critical_automation_as_blocked_not_failed(self):
        trace = build_action_trace(
            request_id="test-blocked",
            raw_input="type my password",
            intent="action_plan",
            provider=None,
            permission={"success": True, "status": "approved", "permission": {"action_name": "desktop_launch", "trust_level": "safe"}},
            action_plan={
                "plan_id": "action-blocked",
                "status": "failed",
                "steps": [
                    {
                        "step_id": "step-1",
                        "action_type": "automation_critical_blocked",
                        "label": "Block critical automation",
                        "status": "critical_blocked",
                    }
                ],
            },
            success=False,
            status="critical_blocked",
            source={"action_status": "critical_blocked", "automation_control": False},
        )

        self.assertEqual(trace["response_mode"], "blocked")
        self.assertEqual(trace["final_status"], "blocked")
        self.assertTrue(trace["automation_state"]["blocked"])


if __name__ == "__main__":
    unittest.main()
