import unittest

from tools.tool_guard import guard_and_execute


class SecurityToolExecutionSmokeTests(unittest.TestCase):
    def test_system_snapshot_requires_confirmation_but_runs_when_confirmed(self):
        result = guard_and_execute("system.snapshot", confirmed=True)
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "executed")


if __name__ == "__main__":
    unittest.main()
