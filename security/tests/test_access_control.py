import unittest

from security.access_control import evaluate_access


class AccessControlTests(unittest.TestCase):
    def test_safe_action_is_allowed(self):
        result = evaluate_access("general")
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "approved")

    def test_critical_action_requires_pin(self):
        result = evaluate_access("file_delete")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "pin")

    def test_private_action_requires_auth_when_username_is_provided(self):
        result = evaluate_access("file_read", username="ghost", confirmed=True)
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "auth_required")


if __name__ == "__main__":
    unittest.main()
