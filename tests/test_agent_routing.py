import unittest

from brain.capability_registry import get_capability, supports_action
from config.agent_registry import get_agent_route


class AgentRoutingTests(unittest.TestCase):
    def test_task_route_matches_capability_registry(self):
        route = get_agent_route("task")
        capability = get_capability("task")
        self.assertIsNotNone(route)
        self.assertIsNotNone(capability)
        self.assertEqual(route.agent, capability.agent)
        self.assertTrue(supports_action("task", "task_add"))


if __name__ == "__main__":
    unittest.main()
