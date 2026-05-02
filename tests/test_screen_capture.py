import sys
import types
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from tools import screen_capture


class ScreenCaptureTests(unittest.TestCase):
    def test_capture_screenshot_returns_image_object(self):
        image = Image.new("RGB", (120, 80), "white")
        with patch.object(screen_capture, "capture_screen_image", return_value=image):
            result = screen_capture.capture_screenshot()

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "captured")
        self.assertIs(result["image"], image)
        self.assertEqual(result["size"], {"width": 120, "height": 80})

    def test_extract_ocr_returns_text_and_positions(self):
        fake_tesseract = types.SimpleNamespace(
            Output=types.SimpleNamespace(DICT="dict"),
            image_to_data=Mock(
                return_value={
                    "text": ["Search", "AI", ""],
                    "conf": ["92", "88", "-1"],
                    "left": [10, 80, 0],
                    "top": [20, 20, 0],
                    "width": [60, 20, 0],
                    "height": [18, 18, 0],
                }
            ),
        )
        with patch.dict(sys.modules, {"pytesseract": fake_tesseract}):
            result = screen_capture.extract_ocr(Image.new("RGB", (100, 50), "white"))

        self.assertTrue(result["success"])
        self.assertEqual(result["visible_text"], "Search AI")
        self.assertEqual(result["ocr_items"][0]["bbox"]["x"], 10)

    def test_detect_ui_elements_finds_buttons_inputs_and_search(self):
        items = [
            {"text": "Search", "bbox": {"x": 10, "y": 10, "width": 120, "height": 20}, "confidence": 91},
            {"text": "Submit", "bbox": {"x": 10, "y": 40, "width": 70, "height": 24}, "confidence": 90},
            {"text": "Type a message here", "bbox": {"x": 10, "y": 80, "width": 240, "height": 26}, "confidence": 86},
        ]

        elements = screen_capture.detect_ui_elements(items, (400, 300))
        kinds = {item["kind"] for item in elements}

        self.assertIn("search_bar", kinds)
        self.assertIn("button", kinds)
        self.assertIn("input_field", kinds)

    def test_sensitive_screen_text_detection(self):
        self.assertTrue(screen_capture.detect_sensitive_screen_text("Checkout payment password"))
        self.assertFalse(screen_capture.detect_sensitive_screen_text("Untitled Notepad notes"))

    def test_screen_context_for_editor_adds_candidate_without_clicking(self):
        with patch.object(
            screen_capture,
            "observe_screen",
            return_value={
                "success": True,
                "status": "observed",
                "size": {"width": 1000, "height": 600},
                "visible_text": "",
                "ui_elements": [],
                "sensitive_detected": False,
                "candidate_element": None,
            },
        ):
            result = screen_capture.screen_context_for_automation("notepad", "type_text")

        self.assertTrue(result["success"])
        self.assertEqual(result["candidate_element"]["kind"], "input_field")
        self.assertTrue(result["confirmation_required"])


if __name__ == "__main__":
    unittest.main()
