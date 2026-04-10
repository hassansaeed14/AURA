import unittest

from security.trust_engine import build_permission_response


class SecurityMemorySmokeTests(unittest.TestCase):
    def test_memory_read_requires_confirmation_by_default(self):
        result = build_permission_response("memory_read")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "needs_confirmation")

    def test_memory_read_can_be_confirmed(self):
        result = build_permission_response("memory_read", confirmed=True)
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "approved")


if __name__ == "__main__":
    unittest.main()
