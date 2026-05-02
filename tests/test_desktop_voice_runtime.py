import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

import api.api_server as api_server
from voice import desktop_voice_runtime as runtime


AVAILABLE_DEPS = {
    "available": True,
    "stt": {"available": True, "supports_microphone": True},
    "microphone": {"available": True, "count": 1, "devices": ["Mock mic"]},
    "tts": {"available": True, "backend": "pyttsx3"},
    "missing": [],
}

MISSING_DEPS = {
    "available": False,
    "stt": {"available": False, "supports_microphone": False},
    "microphone": {"available": False, "count": 0, "devices": []},
    "tts": {"available": False, "backend": "unavailable"},
    "missing": ["speech_recognition", "microphone"],
}


class DesktopVoiceRuntimeTests(unittest.TestCase):
    def tearDown(self):
        runtime.stop_desktop_voice()

    def test_status_reports_unavailable_when_dependencies_missing(self):
        with patch.object(runtime, "_dependency_snapshot", return_value=MISSING_DEPS):
            status = runtime.get_desktop_voice_status()
            started = runtime.start_desktop_voice(start_loop=False)

        self.assertFalse(status["available"])
        self.assertFalse(status["active"])
        self.assertEqual(status["message"], runtime.UNAVAILABLE_MESSAGE)
        self.assertFalse(started["success"])
        self.assertEqual(started["last_error"], runtime.UNAVAILABLE_MESSAGE)

    def test_start_and_stop_status_transitions_without_test_thread(self):
        with patch.object(runtime, "_dependency_snapshot", return_value=AVAILABLE_DEPS):
            started = runtime.start_desktop_voice(session_id="test-session", start_loop=False)
            active_status = runtime.get_desktop_voice_status()
            stopped = runtime.stop_desktop_voice()

        self.assertTrue(started["success"])
        self.assertTrue(active_status["active"])
        self.assertTrue(active_status["listening"])
        self.assertEqual(active_status["state"], "listening")
        self.assertTrue(stopped["success"])
        self.assertFalse(stopped["active"])

    def test_interrupt_resets_processing_and_speaking_state(self):
        with patch.object(runtime, "_dependency_snapshot", return_value=AVAILABLE_DEPS):
            runtime.start_desktop_voice(start_loop=False)
            runtime._set_state(processing=True, speaking=True, listening=False)
            interrupted = runtime.interrupt_desktop_voice()

        self.assertTrue(interrupted["success"])
        self.assertTrue(interrupted["listening"])
        self.assertFalse(interrupted["processing"])
        self.assertFalse(interrupted["speaking"])

    def test_command_routing_uses_normal_runtime_path(self):
        with patch("brain.core_ai.process_command_detailed", return_value={"response": "Done.", "permission": {"permission": {"trust_level": "safe"}}}) as command_mock:
            result = runtime._run_runtime_command("hello", session_id="voice-session", user_profile={"username": "tester"})

        self.assertEqual(result["response"], "Done.")
        command_mock.assert_called_once()
        self.assertEqual(command_mock.call_args.kwargs["session_id"], "voice-session")
        self.assertEqual(command_mock.call_args.kwargs["current_mode"], "real")
        self.assertEqual(command_mock.call_args.kwargs["user_profile"]["username"], "tester")

    def test_sensitive_and_critical_voice_results_are_spoken_as_safe_summaries(self):
        sensitive = {
            "response": "Opening Notepad... Do you want me to control your keyboard/mouse?",
            "automation_confirmation_required": True,
            "permission": {"permission": {"trust_level": "sensitive"}},
        }
        critical = {
            "response": "I can't perform destructive, payment, password, banking, or account automation.",
            "action_steps": [{"action_type": "automation_critical_blocked"}],
        }

        self.assertEqual(runtime._safe_spoken_text(sensitive, sensitive["response"]), "This needs your approval in AURA before I can continue.")
        self.assertEqual(runtime._safe_spoken_text(critical, critical["response"]), "I blocked that action for safety.")

    def test_process_command_does_not_speak_sensitive_raw_content(self):
        with patch.object(runtime, "_dependency_snapshot", return_value=AVAILABLE_DEPS):
            runtime.start_desktop_voice(start_loop=False)
        with patch.object(runtime, "_run_runtime_command", return_value={
            "response": "Opening Notepad... Do you want me to control your keyboard/mouse?",
            "automation_confirmation_required": True,
            "permission": {"permission": {"trust_level": "sensitive"}},
        }), patch.object(runtime, "speak_desktop_text", return_value={"success": True, "status": "spoken"}) as speak_mock:
            result = runtime.process_desktop_voice_command("open notepad and type hello", speak=True)

        self.assertEqual(result["spoken_text"], "This needs your approval in AURA before I can continue.")
        speak_mock.assert_called_once_with("This needs your approval in AURA before I can continue.")


class DesktopVoiceApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api_server.app)

    def test_desktop_voice_api_endpoints_return_clean_json(self):
        with patch.object(api_server, "requires_first_run_setup", return_value=False), patch.object(
            api_server,
            "start_desktop_voice",
            return_value={"success": True, "active": True, "listening": True, "message": 'Listening for "Hey AURA".'},
        ) as start_mock, patch.object(
            api_server,
            "stop_desktop_voice",
            return_value={"success": True, "active": False, "message": "Desktop voice runtime stopped."},
        ) as stop_mock, patch.object(
            api_server,
            "interrupt_desktop_voice",
            return_value={"success": True, "active": True, "message": "Desktop voice runtime interrupted."},
        ) as interrupt_mock:
            start_response = self.client.post("/api/voice/desktop/start")
            stop_response = self.client.post("/api/voice/desktop/stop")
            interrupt_response = self.client.post("/api/voice/desktop/interrupt")

        self.assertEqual(start_response.status_code, 200)
        self.assertTrue(start_response.json()["active"])
        self.assertEqual(stop_response.status_code, 200)
        self.assertFalse(stop_response.json()["active"])
        self.assertEqual(interrupt_response.status_code, 200)
        self.assertIn("interrupted", interrupt_response.json()["message"])
        start_mock.assert_called_once()
        stop_mock.assert_called_once()
        interrupt_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
