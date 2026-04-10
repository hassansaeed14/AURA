import unittest

from brain.decision_engine import (
    build_decision_summary,
    format_multi_response,
    should_use_agent,
)


class DecisionEngineTests(unittest.TestCase):
    def test_should_use_agent_respects_confidence_threshold(self):
        router = {"translation": lambda command: command}
        self.assertTrue(should_use_agent("translation", 0.7, router))
        self.assertFalse(should_use_agent("translation", 0.4, router))
        self.assertFalse(should_use_agent("unknown", 0.9, router))

    def test_build_decision_summary_marks_low_confidence_caution_zone(self):
        summary = build_decision_summary("research", 0.4, {"research": lambda command: command})
        self.assertFalse(summary["fallback"])
        self.assertFalse(summary["use_agent"])
        self.assertTrue(summary["low_confidence"])
        self.assertEqual(summary["decision_reason"], "low_confidence_caution_zone")

    def test_format_multi_response_numbers_meaningful_results(self):
        formatted = format_multi_response(["First result", "", "Second result"])
        self.assertIn("1. First result", formatted)
        self.assertIn("2. Second result", formatted)


if __name__ == "__main__":
    unittest.main()
