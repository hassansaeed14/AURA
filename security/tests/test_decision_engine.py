import unittest

from brain.decision_engine import build_decision_summary
from security.access_control import evaluate_access


class SecurityDecisionEngineSmokeTests(unittest.TestCase):
    def test_decision_summary_stays_in_general_route_for_low_confidence(self):
        summary = build_decision_summary("file", 0.2, {"file": lambda command: command})
        self.assertTrue(summary["fallback"])
        self.assertEqual(summary["final_route"], "general")

    def test_private_action_is_allowed_after_confirmation(self):
        result = evaluate_access("file_read", confirmed=True)
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "approved")


if __name__ == "__main__":
    unittest.main()
