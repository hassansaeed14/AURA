import unittest

from agents.registry import get_agent_summary, list_agents, validate_registry


class AgentRegistryTests(unittest.TestCase):
    def test_registry_entries_follow_capability_doctrine(self):
        self.assertEqual(validate_registry(), [])

    def test_agent_listing_exposes_capability_metadata(self):
        agent = list_agents()[0]
        self.assertIn("capability_mode", agent)
        self.assertIn("trust_level", agent)
        self.assertIn("integration_path", agent)
        self.assertIn("ui_claim", agent)

    def test_summary_tracks_capability_modes(self):
        summary = get_agent_summary()
        self.assertGreater(summary["capability_modes"]["real"], 0)
        self.assertGreater(summary["capability_modes"]["hybrid"], 0)
        self.assertGreater(summary["capability_modes"]["placeholder"], 0)
        self.assertEqual(summary["connected"], summary["total"] - summary["placeholders"])


if __name__ == "__main__":
    unittest.main()
