import inspect
import unittest
from unittest.mock import Mock, patch

from config.permissions import get_action_policy
from tools import os_automation


class OSAutoFakeWindow:
    def __init__(self, title):
        self.title = title
        self.activated = False

    def activate(self):
        self.activated = True


class OSAutoFakePyAutoGUI:
    def __init__(self, title="Untitled - Notepad"):
        self.FAILSAFE = False
        self.PAUSE = 0
        self.active = OSAutoFakeWindow(title)
        self.windows = [self.active]
        self.write = Mock()
        self.press = Mock()
        self.hotkey = Mock()
        self.scroll = Mock()

    def getActiveWindow(self):
        return self.active

    def getWindowsWithTitle(self, _title):
        return self.windows


class OSAutomationTests(unittest.TestCase):
    def setUp(self):
        os_automation.reset_stop_flag()
        self.screen_patch = patch.object(
            os_automation,
            "screen_context_for_automation",
            return_value={
                "success": True,
                "status": "observed",
                "sensitive_detected": False,
                "candidate_element": {"kind": "input_field", "label": "active editor"},
                "ui_elements": [],
                "validation_reason": "Screen context observed.",
            },
        )
        self.screen_mock = self.screen_patch.start()

    def tearDown(self):
        self.screen_patch.stop()

    def test_unsupported_app_blocked(self):
        result = os_automation.type_text("hello", "terminal")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "unsupported")

    def test_sensitive_window_blocked(self):
        fake = OSAutoFakePyAutoGUI("Checkout payment - Chrome")
        with patch.object(os_automation, "_pyautogui", return_value=fake):
            result = os_automation.type_text("hello", "chrome")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "sensitive_window_blocked")

    def test_wrong_window_blocked(self):
        fake = OSAutoFakePyAutoGUI("Untitled - Notepad")
        with patch.object(os_automation, "_pyautogui", return_value=fake):
            result = os_automation.press_key("enter", "chrome")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "wrong_active_window")
        fake.press.assert_not_called()

    def test_critical_text_blocked(self):
        fake = OSAutoFakePyAutoGUI("Untitled - Notepad")
        with patch.object(os_automation, "_pyautogui", return_value=fake):
            result = os_automation.type_text("my password is secret", "notepad")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "critical_blocked")
        self.assertEqual(result["trust_level"], "critical")
        fake.write.assert_not_called()

    def test_sensitive_terms_include_bank_login_credit_card_and_credentials(self):
        fake = OSAutoFakePyAutoGUI("Untitled - Notepad")
        with patch.object(os_automation, "_pyautogui", return_value=fake):
            for text in ("bank details", "login token", "credit card number", "credentials here"):
                result = os_automation.type_text(text, "notepad")
                self.assertFalse(result["success"], text)
                self.assertEqual(result["status"], "critical_blocked", text)

    def test_allowed_typing_in_notepad_mocked_safely(self):
        fake = OSAutoFakePyAutoGUI("Untitled - Notepad")
        with patch.object(os_automation, "_pyautogui", return_value=fake):
            result = os_automation.type_text("hello", "notepad")

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "typed")
        fake.write.assert_called_once_with("hello", interval=os_automation.TYPE_CHARACTER_INTERVAL_SECONDS)
        self.screen_mock.assert_called_with("notepad", "type_text", active_window="Untitled - Notepad")
        self.assertIn("screen_context", result)
        self.assertTrue(result["screen_validation"]["allowed"])
        self.assertEqual(result["control_flow"]["state"], "success")
        self.assertEqual(
            [transition["state"] for transition in result["control_flow"]["transitions"]],
            ["pending", "approved", "executing", "success"],
        )

    def test_sensitive_screen_blocks_before_typing(self):
        self.screen_mock.return_value = {
            "success": True,
            "status": "observed",
            "sensitive_detected": True,
            "visible_text": "Checkout payment password",
        }
        fake = OSAutoFakePyAutoGUI("Untitled - Notepad")
        with patch.object(os_automation, "_pyautogui", return_value=fake):
            result = os_automation.type_text("hello", "notepad")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "sensitive_screen_blocked")
        self.assertIn("screen_context", result)
        self.assertFalse(result["screen_validation"]["allowed"])
        fake.write.assert_not_called()

    def test_login_screen_blocks_before_typing(self):
        self.screen_mock.return_value = {
            "success": True,
            "status": "observed",
            "sensitive_detected": True,
            "visible_text": "Login password OTP",
            "ui_elements": [{"kind": "input_field", "label": "Password"}],
        }
        fake = OSAutoFakePyAutoGUI("Google - Chrome")
        with patch.object(os_automation, "_pyautogui", return_value=fake):
            result = os_automation.type_text("hello", "chrome")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "sensitive_screen_blocked")
        fake.write.assert_not_called()

    def test_screen_observation_failure_blocks_control(self):
        self.screen_mock.return_value = {
            "success": False,
            "status": "ocr_unavailable",
            "message": "OCR unavailable.",
            "validation_reason": "Screen observation failed.",
        }
        fake = OSAutoFakePyAutoGUI("Untitled - Notepad")
        with patch.object(os_automation, "_pyautogui", return_value=fake):
            result = os_automation.type_text("hello", "notepad")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "screen_context_unavailable")
        self.assertFalse(result["screen_validation"]["allowed"])
        fake.write.assert_not_called()

    def test_missing_editable_ui_blocks_typing(self):
        self.screen_mock.return_value = {
            "success": True,
            "status": "observed",
            "sensitive_detected": False,
            "candidate_element": None,
            "ui_elements": [{"kind": "button", "label": "Save"}],
            "validation_reason": "Screen context observed.",
        }
        fake = OSAutoFakePyAutoGUI("Google - Chrome")
        with patch.object(os_automation, "_pyautogui", return_value=fake):
            result = os_automation.type_text("hello", "chrome")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "expected_ui_not_found")
        self.assertFalse(result["screen_validation"]["allowed"])
        fake.write.assert_not_called()

    def test_stop_flag_blocks_control(self):
        os_automation.request_stop()
        fake = OSAutoFakePyAutoGUI("Untitled - Notepad")
        with patch.object(os_automation, "_pyautogui", return_value=fake):
            result = os_automation.type_text("hello", "notepad")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "interrupted")
        self.assertEqual(result["control_flow"]["state"], "interrupted")
        fake.write.assert_not_called()

    def test_stop_interrupts_typing_between_chunks(self):
        fake = OSAutoFakePyAutoGUI("Untitled - Notepad")

        def stop_after_first_chunk(*_args, **_kwargs):
            os_automation.request_stop()

        fake.write.side_effect = stop_after_first_chunk
        long_text = "x" * (os_automation.TYPE_CHUNK_SIZE + 5)
        with patch.object(os_automation, "_pyautogui", return_value=fake), patch.object(os_automation.time, "sleep"):
            result = os_automation.type_text(long_text, "notepad")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "interrupted")
        self.assertEqual(result["control_flow"]["state"], "interrupted")
        self.assertEqual(fake.write.call_count, 1)

    def test_stop_interrupts_key_hotkey_and_scroll(self):
        fake = OSAutoFakePyAutoGUI("Untitled - Notepad")
        with patch.object(os_automation, "_pyautogui", return_value=fake):
            os_automation.request_stop()
            self.assertEqual(os_automation.press_key("enter", "notepad")["status"], "interrupted")
            os_automation.request_stop()
            self.assertEqual(os_automation.hotkey(["ctrl", "a"], "notepad")["status"], "interrupted")
            os_automation.request_stop()
            self.assertEqual(os_automation.scroll(3, "notepad")["status"], "interrupted")

        fake.press.assert_not_called()
        fake.hotkey.assert_not_called()
        fake.scroll.assert_not_called()

    def test_os_action_logs_success_blocked_and_stopped(self):
        fake = OSAutoFakePyAutoGUI("Untitled - Notepad")
        with patch.object(os_automation, "_pyautogui", return_value=fake), patch("builtins.print") as print_mock:
            os_automation.type_text("hello", "notepad")
            os_automation.type_text("password", "notepad")
            os_automation.request_stop()
            os_automation.press_key("enter", "notepad")

        lines = [" ".join(str(part) for part in call.args) for call in print_mock.call_args_list]
        self.assertTrue(any("[OS ACTION] type_text" in line and "success" in line for line in lines))
        self.assertTrue(any("[OS BLOCKED] sensitive content" in line for line in lines))
        self.assertTrue(any("[OS INTERRUPTED] user interrupt" in line for line in lines))

    def test_duplicate_control_action_is_blocked_while_active(self):
        fake = OSAutoFakePyAutoGUI("Untitled - Notepad")
        nested_results = []

        def nested_type_attempt(*_args, **_kwargs):
            nested_results.append(os_automation.type_text("nested", "notepad"))

        fake.write.side_effect = nested_type_attempt
        with patch.object(os_automation, "_pyautogui", return_value=fake):
            result = os_automation.type_text("hello", "notepad")

        self.assertTrue(result["success"])
        self.assertEqual(fake.write.call_count, 1)
        self.assertEqual(nested_results[0]["status"], "automation_busy")
        self.assertEqual(nested_results[0]["control_flow"]["state"], "blocked")

    def test_focus_change_during_typing_interrupts_action(self):
        fake = OSAutoFakePyAutoGUI("Untitled - Notepad")
        titles = [
            "Untitled - Notepad",
            "Untitled - Notepad",
            "Calculator",
        ]

        def active_window_sequence():
            title = titles.pop(0) if titles else "Calculator"
            fake.active = OSAutoFakeWindow(title)
            return fake.active

        fake.getActiveWindow = Mock(side_effect=active_window_sequence)
        with patch.object(os_automation, "_pyautogui", return_value=fake):
            result = os_automation.type_text("hello", "notepad")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "focus_changed")
        self.assertEqual(result["control_flow"]["state"], "interrupted")
        self.assertEqual(fake.write.call_count, 1)

    def test_failed_execution_does_not_retry_or_repeat_typing(self):
        fake = OSAutoFakePyAutoGUI("Untitled - Notepad")
        fake.write.side_effect = RuntimeError("keyboard backend failed")

        with patch.object(os_automation, "_pyautogui", return_value=fake):
            result = os_automation.type_text("hello", "notepad")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "type_failed")
        self.assertEqual(result["control_flow"]["state"], "failed")
        self.assertTrue(result["single_execution"])
        self.assertEqual(fake.write.call_count, 1)

    def test_pyautogui_not_directly_exposed_and_no_shell(self):
        self.assertNotIn("pyautogui", os_automation.__all__)
        source = inspect.getsource(os_automation)
        self.assertIn("module.FAILSAFE = True", source)
        self.assertNotIn("shell=True", source)
        self.assertNotIn("subprocess", source)

    def test_automation_trust_classification_registered(self):
        self.assertEqual(get_action_policy("os_automation_focus").trust_level, "safe")
        self.assertEqual(get_action_policy("os_automation_control").trust_level, "sensitive")
        self.assertEqual(get_action_policy("os_automation_critical").trust_level, "critical")


if __name__ == "__main__":
    unittest.main()
