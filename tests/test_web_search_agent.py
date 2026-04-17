import unittest
from unittest.mock import Mock

from agents.integration.web_search_agent import (
    GROQ_MODELS_SOURCE,
    OPENAI_STATUS_SOURCE,
    SearchResultItem,
    WebSearchAgent,
)


class WebSearchAgentTests(unittest.TestCase):
    def test_search_uses_official_fallback_when_instant_answer_has_no_results(self):
        agent = WebSearchAgent()
        agent.search_client = Mock()
        agent.search_client.fetch_json.return_value = {
            "Heading": "",
            "Abstract": "",
            "RelatedTopics": [],
        }
        agent.memory_manager = Mock()
        agent.memory_manager.maybe_store.return_value = None
        agent._official_live_search_fallback = Mock(
            return_value=(
                SearchResultItem(
                    heading="OpenAI API status",
                    abstract="OpenAI's official status page currently reports: All Systems Operational.",
                    related_topics=["Source: status.openai.com"],
                ),
                OPENAI_STATUS_SOURCE,
            )
        )

        result = agent.search("what is OpenAI's current API status")

        self.assertTrue(result["success"])
        self.assertEqual(result["source"], OPENAI_STATUS_SOURCE)
        self.assertEqual(result["data"]["heading"], "OpenAI API status")

    def test_official_openai_status_fallback_parses_status_json(self):
        agent = WebSearchAgent()
        agent.search_client = Mock()
        agent.search_client.fetch_json.return_value = {
            "status": {"description": "All Systems Operational", "indicator": "none"},
            "page": {"updated_at": "2026-04-17T12:00:00Z"},
        }

        parsed = agent._official_live_search_fallback("what is OpenAI's current API status")

        self.assertIsNotNone(parsed)
        item, source = parsed
        self.assertEqual(source, OPENAI_STATUS_SOURCE)
        self.assertIn("All Systems Operational", item.abstract)
        self.assertIn("status.openai.com", " ".join(item.related_topics))

    def test_official_groq_pricing_fallback_extracts_model_prices(self):
        agent = WebSearchAgent()
        agent.search_client = Mock()
        fake_response = Mock()
        fake_response.text = """
        MODEL ID
        SPEED
        PRICE PER
        1M TOKENS
        Llama 3.1 8B
        llama-3.1-8b-instant
        560
        $0.05
        input
        $0.08
        output
        Llama 3.3 70B
        llama-3.3-70b-versatile
        280
        $0.59
        input
        $0.79
        output
        """
        agent.search_client.fetch_html.return_value = fake_response

        parsed = agent._official_live_search_fallback("what is the latest Groq API pricing")

        self.assertIsNotNone(parsed)
        item, source = parsed
        self.assertEqual(source, GROQ_MODELS_SOURCE)
        self.assertIn("Groq's official models page", item.abstract)
        self.assertIn("$0.59", item.abstract)


if __name__ == "__main__":
    unittest.main()
