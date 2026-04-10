import unittest

from voice.noise_filter import clean_transcript_text
from voice.voice_pipeline import process_voice_text
from voice.wake_word import detect_wake_word


class VoicePipelineTests(unittest.TestCase):
    def test_wake_word_must_match_at_start(self):
        result = detect_wake_word("I think hey aura is a cool phrase")
        self.assertFalse(result["detected"])

    def test_noise_filter_preserves_meaning_without_forcing_lowercase(self):
        cleaned = clean_transcript_text("Um Please open Chrome, plz")
        self.assertEqual(cleaned, "Please open Chrome, please")

    def test_voice_pipeline_handles_empty_command_after_wake_word(self):
        result = process_voice_text("Hey Aura")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "empty_command")


if __name__ == "__main__":
    unittest.main()
