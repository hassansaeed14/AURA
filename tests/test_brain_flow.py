import unittest

from brain.command_splitter import split_commands
from brain.entity_parser import parse_entities
from brain.planner import build_execution_plan


class BrainFlowTests(unittest.TestCase):
    def test_command_splitter_preserves_order_for_multi_action_input(self):
        result = split_commands("open Chrome and remind me at 5 then translate this to Urdu")
        self.assertEqual(result, ["open Chrome", "remind me at 5", "translate this to Urdu"])

    def test_entity_parser_extracts_temporal_and_file_entities(self):
        parsed = parse_entities("summarize Aura Report.docx then remind me to review it tomorrow at 5 pm")
        self.assertIn("Aura Report.docx", parsed.files)
        self.assertTrue(parsed.dates)
        self.assertIn("5 pm", [value.lower() for value in parsed.times])
        self.assertEqual(parsed.reminder_text, "review it")

    def test_planner_marks_follow_up_step_dependency(self):
        plan = build_execution_plan("summarize Aura Report.docx then save it")
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.steps[1].depends_on, [1])


if __name__ == "__main__":
    unittest.main()
