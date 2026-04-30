import unittest
from unittest.mock import Mock, patch

from tools import desktop_controller


class DesktopControllerTests(unittest.TestCase):
    def test_supported_desktop_apps_include_truthful_availability_fields(self):
        with patch.object(
            desktop_controller,
            "_resolve_launch_command",
            side_effect=lambda spec: ["C:\\safe.exe"] if spec["label"] in {"Notepad", "Calculator"} else None,
        ):
            apps = desktop_controller.get_supported_desktop_apps()

        self.assertEqual([app["app_id"] for app in apps], ["chrome", "notepad", "calculator", "vs code"])
        self.assertEqual(apps[0]["display_name"], "Chrome")
        self.assertEqual(apps[1]["aliases"], ["notepad"])
        self.assertFalse(apps[0]["available"])
        self.assertEqual(apps[1]["status"], "available")

    def test_normalize_application_name_accepts_supported_aliases(self):
        self.assertEqual(desktop_controller.normalize_application_name("google chrome"), "chrome")
        self.assertEqual(desktop_controller.normalize_application_name("calc"), "calculator")
        self.assertEqual(desktop_controller.normalize_application_name("visual studio code"), "vs code")

    def test_normalize_application_name_rejects_path_like_input(self):
        self.assertIsNone(desktop_controller.normalize_application_name(r"..\Windows\System32\cmd.exe"))
        self.assertIsNone(desktop_controller.normalize_application_name(r"C:\Windows\System32\notepad.exe"))

    def test_open_application_launches_whitelisted_notepad(self):
        process = Mock(pid=4242)
        with patch.object(
            desktop_controller,
            "get_application_availability",
            return_value={
                "supported": True,
                "available": True,
                "status": "available",
                "app_name": "notepad",
                "label": "Notepad",
                "aliases": ["notepad"],
                "launch_command": ["C:\\Windows\\System32\\notepad.exe"],
            },
        ), patch.object(
            desktop_controller.subprocess,
            "Popen",
            return_value=process,
        ) as popen_mock:
            result = desktop_controller.open_application("notepad")

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "opened")
        self.assertEqual(result["app_name"], "notepad")
        self.assertEqual(result["message"], "Opening Notepad.")
        self.assertEqual(result["pid"], 4242)
        popen_mock.assert_called_once_with(["C:\\Windows\\System32\\notepad.exe"], shell=False)

    def test_open_application_returns_clean_message_when_unavailable(self):
        with patch.object(
            desktop_controller,
            "get_application_availability",
            return_value={
                "supported": True,
                "available": False,
                "status": "unavailable",
                "app_name": "chrome",
                "label": "Chrome",
                "aliases": ["chrome", "google chrome"],
                "launch_command": None,
            },
        ):
            result = desktop_controller.open_application("chrome")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["message"], "I couldn't find Chrome on this system.")

    def test_unsupported_application_is_rejected_cleanly(self):
        result = desktop_controller.open_application("photoshop")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["message"], "I can't open that yet.")

    def test_launch_failure_returns_clear_reason(self):
        with patch.object(
            desktop_controller,
            "get_application_availability",
            return_value={
                "supported": True,
                "available": True,
                "status": "available",
                "app_name": "vs code",
                "label": "VS Code",
                "aliases": ["vs code", "vscode"],
                "launch_command": ["C:\\Users\\beast\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe"],
            },
        ), patch.object(
            desktop_controller.subprocess,
            "Popen",
            side_effect=OSError("Access is denied"),
        ):
            result = desktop_controller.open_application("vs code")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "launch_failed")
        self.assertIn("I couldn't open VS Code", result["message"])
        self.assertIn("Access is denied", result["message"])

    def test_open_chrome_search_uses_safe_url_argument_without_shell(self):
        process = Mock(pid=5151)
        with patch.object(
            desktop_controller,
            "get_application_availability",
            return_value={
                "supported": True,
                "available": True,
                "status": "available",
                "app_name": "chrome",
                "label": "Chrome",
                "aliases": ["chrome", "google chrome"],
                "launch_command": ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"],
            },
        ), patch.object(
            desktop_controller.subprocess,
            "Popen",
            return_value=process,
        ) as popen_mock:
            result = desktop_controller.open_chrome_search("AI trends")

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "searched")
        self.assertEqual(result["query"], "AI trends")
        launch_args = popen_mock.call_args.args[0]
        self.assertEqual(launch_args[0], "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe")
        self.assertIn("https://www.google.com/search?", launch_args[1])
        self.assertIn("AI+trends", launch_args[1])
        popen_mock.assert_called_once()
        self.assertFalse(popen_mock.call_args.kwargs["shell"])

    def test_open_chrome_search_rejects_empty_query(self):
        result = desktop_controller.open_chrome_search("   ")

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "invalid_query")
        self.assertIn("search phrase", result["message"])


if __name__ == "__main__":
    unittest.main()
