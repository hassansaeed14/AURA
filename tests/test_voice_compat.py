import importlib
import unittest

import voice.speech_to_text as speech_to_text
import voice.text_to_speech as text_to_speech


class VoiceCompatibilityTests(unittest.TestCase):
    def test_text_to_speech_exposes_legacy_cli_functions(self):
        self.assertTrue(callable(text_to_speech.speak))
        self.assertTrue(callable(text_to_speech.stop_speaking))

    def test_speech_to_text_exposes_legacy_cli_listen_function(self):
        self.assertTrue(callable(speech_to_text.listen))

    def test_main_module_imports_successfully(self):
        main_module = importlib.import_module("main")
        self.assertTrue(callable(main_module.start_goku))


if __name__ == "__main__":
    unittest.main()
