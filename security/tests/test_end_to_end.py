import unittest
from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import patch

import security.session_manager as session_manager
from security.access_control import evaluate_access


class SecurityEndToEndSmokeTests(unittest.TestCase):
    def test_sensitive_action_can_be_reused_after_session_approval(self):
        temp_root = Path(mkdtemp(dir=r"D:\HeyGoku"))
        with patch.object(session_manager, "SESSION_FILE", temp_root / "sessions.json"):
            session_manager.approve_action("security-e2e", "screenshot", minutes=5)
            result = evaluate_access("screenshot", session_id="security-e2e")

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "approved")


if __name__ == "__main__":
    unittest.main()
