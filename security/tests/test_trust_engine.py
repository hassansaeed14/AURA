import unittest

from security.trust_engine import build_permission_response, evaluate_action


class TrustEngineTests(unittest.TestCase):
    def test_safe_action_is_auto_approved(self):
        decision = evaluate_action("weather")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason_code, "SAFE_ACTION")

    def test_private_action_requires_confirmation(self):
        result = build_permission_response("file_read")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "needs_confirmation")


if __name__ == "__main__":
    unittest.main()
