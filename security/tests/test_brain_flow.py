import unittest

from brain.command_splitter import split_commands
from security.trust_engine import build_permission_response


class SecurityBrainFlowSmokeTests(unittest.TestCase):
    def test_split_commands_preserves_critical_follow_up(self):
        parts = split_commands("read file and delete file")
        self.assertEqual(parts, ["read file", "delete file"])

    def test_critical_permission_response_requires_pin(self):
        result = build_permission_response("file_delete")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "needs_pin")


if __name__ == "__main__":
    unittest.main()
