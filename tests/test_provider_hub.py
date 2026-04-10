import unittest
from unittest.mock import patch

import brain.provider_hub as provider_hub


class ProviderHubTests(unittest.TestCase):
    def test_provider_statuses_cover_major_backends(self):
        statuses = provider_hub.list_provider_statuses()
        provider_ids = {item["provider"] for item in statuses}
        self.assertTrue({"openai", "groq", "claude", "gemini", "ollama"}.issubset(provider_ids))

    def test_pick_provider_prefers_available_provider(self):
        fake_statuses = {
            "openai": provider_hub.ProviderStatus("openai", "gpt", "hybrid", False, False, True, "missing"),
            "groq": provider_hub.ProviderStatus("groq", "llama", "real", True, True, True, "ready"),
        }

        with patch.object(provider_hub, "get_provider_status", side_effect=lambda provider: fake_statuses.get(provider) or provider_hub.ProviderStatus(provider, "x", "hybrid", False, False, True, "missing")):
            chosen = provider_hub.pick_provider(preferred="router")

        self.assertEqual(chosen, "groq")


if __name__ == "__main__":
    unittest.main()
