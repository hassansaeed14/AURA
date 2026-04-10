import unittest
from unittest.mock import patch

import brain.runtime_core as runtime_core
import voice.voice_pipeline as voice_pipeline


class EndToEndTests(unittest.TestCase):
    def test_multi_command_runtime_flow_keeps_steps_and_permissions_honest(self):
        with patch.object(runtime_core, "store_and_learn", lambda *args, **kwargs: None), patch.object(
            runtime_core,
            "update_context_from_command",
            lambda *args, **kwargs: None,
        ), patch.object(
            runtime_core,
            "record_reflection",
            lambda *args, **kwargs: None,
        ):
            result = runtime_core.process_command_detailed("what time is it and what date is it")

        self.assertEqual(result["intent"], "multi_command")
        self.assertEqual(len(result["plan"]), 2)
        self.assertTrue(result["permission"]["success"])
        self.assertEqual(result["permission"]["status"], "aggregated")

    def test_voice_pipeline_detects_wake_word_and_routes_text(self):
        fake_result = {
            "intent": "time",
            "detected_intent": "time",
            "confidence": 1.0,
            "response": "The current time is 10:00 AM.",
        }
        with patch.object(voice_pipeline, "process_command_detailed", return_value=fake_result):
            result = voice_pipeline.process_voice_text("Hey Aura what time is it")

        self.assertTrue(result["success"])
        self.assertTrue(result["wake_word"]["detected"])
        self.assertEqual(result["command_text"], "what time is it")
        self.assertEqual(result["result"]["intent"], "time")


if __name__ == "__main__":
    unittest.main()
