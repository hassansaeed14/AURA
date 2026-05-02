import unittest
from unittest.mock import Mock, patch

from tools import browser_actions


class BrowserActionsTests(unittest.TestCase):
    def test_normalize_browser_url_allows_only_http_https(self):
        self.assertEqual(browser_actions.normalize_browser_url("example.com"), "https://example.com")
        self.assertEqual(browser_actions.normalize_browser_url("https://example.com/docs"), "https://example.com/docs")
        self.assertIsNone(browser_actions.normalize_browser_url("javascript:alert(1)"))
        self.assertIsNone(browser_actions.normalize_browser_url("file:///C:/Windows/System32/cmd.exe"))
        self.assertIsNone(browser_actions.normalize_browser_url("https://user:pass@example.com"))

    def test_open_url_launches_validated_url_without_shell(self):
        process = Mock(pid=6262)
        with patch.object(
            browser_actions,
            "get_application_availability",
            return_value={
                "available": True,
                "launch_command": ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"],
            },
        ), patch.object(browser_actions.subprocess, "Popen", return_value=process) as popen_mock:
            result = browser_actions.open_url("example.com")

        self.assertTrue(result["success"])
        self.assertTrue(result["verified"])
        self.assertEqual(result["status"], "opened_url")
        self.assertEqual(result["url"], "https://example.com")
        popen_mock.assert_called_once_with(
            ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "https://example.com"],
            shell=False,
        )

    def test_search_query_uses_controlled_google_url(self):
        process = Mock(pid=6263)
        with patch.object(
            browser_actions,
            "get_application_availability",
            return_value={
                "available": True,
                "launch_command": ["C:\\Chrome\\chrome.exe"],
            },
        ), patch.object(browser_actions.subprocess, "Popen", return_value=process) as popen_mock:
            result = browser_actions.search_query("AI trends")

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "searched")
        self.assertIn("https://www.google.com/search?", result["url"])
        self.assertIn("AI+trends", result["url"])
        self.assertFalse(popen_mock.call_args.kwargs["shell"])

    def test_open_new_tab_uses_chrome_new_tab_flag_without_shell(self):
        process = Mock(pid=6265)
        with patch.object(
            browser_actions,
            "get_application_availability",
            return_value={
                "available": True,
                "launch_command": ["C:\\Chrome\\chrome.exe"],
            },
        ), patch.object(browser_actions.subprocess, "Popen", return_value=process) as popen_mock:
            result = browser_actions.open_new_tab()

        self.assertTrue(result["success"])
        self.assertTrue(result["verified"])
        self.assertEqual(result["status"], "new_tab_opened")
        popen_mock.assert_called_once_with(["C:\\Chrome\\chrome.exe", "--new-tab"], shell=False)

    def test_navigate_to_url_has_navigation_status(self):
        process = Mock(pid=6266)
        with patch.object(
            browser_actions,
            "get_application_availability",
            return_value={
                "available": True,
                "launch_command": ["C:\\Chrome\\chrome.exe"],
            },
        ), patch.object(browser_actions.subprocess, "Popen", return_value=process):
            result = browser_actions.navigate_to_url("example.com")

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "navigated_url")
        self.assertEqual(result["url"], "https://example.com")

    def test_rerun_search_has_distinct_status(self):
        process = Mock(pid=6267)
        with patch.object(
            browser_actions,
            "get_application_availability",
            return_value={
                "available": True,
                "launch_command": ["C:\\Chrome\\chrome.exe"],
            },
        ), patch.object(browser_actions.subprocess, "Popen", return_value=process):
            result = browser_actions.rerun_search("AI trends")

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "reran_search")
        self.assertTrue(result["rerun"])

    def test_open_search_result_uses_top_result_google_url_without_scraping(self):
        process = Mock(pid=6264)
        with patch.object(
            browser_actions,
            "get_application_availability",
            return_value={
                "available": True,
                "launch_command": ["C:\\Chrome\\chrome.exe"],
            },
        ), patch.object(browser_actions.subprocess, "Popen", return_value=process):
            result = browser_actions.open_search_result("Python docs")

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "top_result_requested")
        self.assertIn("btnI=I", result["url"])
        self.assertTrue(result["top_result_only"])

    def test_open_next_result_is_limited_google_url(self):
        process = Mock(pid=6268)
        with patch.object(
            browser_actions,
            "get_application_availability",
            return_value={
                "available": True,
                "launch_command": ["C:\\Chrome\\chrome.exe"],
            },
        ), patch.object(browser_actions.subprocess, "Popen", return_value=process):
            result = browser_actions.open_search_result("Python docs", result_index=2)

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "next_result_requested")
        self.assertIn("start=1", result["url"])
        self.assertEqual(result["result_index"], 2)

    def test_browser_action_fails_cleanly_when_chrome_unavailable(self):
        with patch.object(
            browser_actions,
            "get_application_availability",
            return_value={"available": False, "launch_command": None},
        ):
            result = browser_actions.open_url("example.com")

        self.assertFalse(result["success"])
        self.assertFalse(result["verified"])
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("couldn't find Chrome", result["message"])


if __name__ == "__main__":
    unittest.main()
