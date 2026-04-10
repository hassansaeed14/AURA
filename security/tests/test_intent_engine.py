import unittest

from brain.intent_engine import detect_intent_with_confidence
from security.trust_engine import build_permission_response


class SecurityIntentSmokeTests(unittest.TestCase):
    def test_screenshot_intent_is_detected(self):
        intent, confidence = detect_intent_with_confidence("take a screenshot")
        self.assertEqual(intent, "screenshot")
        self.assertGreaterEqual(confidence, 0.35)

    def test_detected_screenshot_permission_requires_session(self):
        result = build_permission_response("screenshot")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "needs_session_approval")


if __name__ == "__main__":
    unittest.main()
