import unittest

from config.agent_registry import get_agent_route
from security.access_control import evaluate_access


class SecurityAgentRoutingSmokeTests(unittest.TestCase):
    def test_agent_route_exists_for_task_intent(self):
        route = get_agent_route("task")
        self.assertIsNotNone(route)
        self.assertEqual(route.agent, "task")

    def test_private_file_read_requires_confirmation(self):
        result = evaluate_access("file_read")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "confirm")


if __name__ == "__main__":
    unittest.main()
