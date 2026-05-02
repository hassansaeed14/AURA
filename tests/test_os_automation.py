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
        fake.write.assert_called_once_with("hello", interval=0)
        self.screen_mock.assert_called_with("notepad", "type_text")

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
        fake.write.assert_not_called()

    def test_stop_flag_blocks_control(self):
        os_automation.request_stop()
        fake = OSAutoFakePyAutoGUI("Untitled - Notepad")
        with patch.object(os_automation, "_pyautogui", return_value=fake):
            result = os_automation.type_text("hello", "notepad")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "stopped")
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
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(fake.write.call_count, 1)

    def test_stop_interrupts_key_hotkey_and_scroll(self):
        fake = OSAutoFakePyAutoGUI("Untitled - Notepad")
        with patch.object(os_automation, "_pyautogui", return_value=fake):
            os_automation.request_stop()
            self.assertEqual(os_automation.press_key("enter", "notepad")["status"], "stopped")
            os_automation.request_stop()
            self.assertEqual(os_automation.hotkey(["ctrl", "a"], "notepad")["status"], "stopped")
            os_automation.request_stop()
            self.assertEqual(os_automation.scroll(3, "notepad")["status"], "stopped")

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
        self.assertTrue(any("[OS STOPPED] user interrupt" in line for line in lines))

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
