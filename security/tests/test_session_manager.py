import unittest
from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import patch

import security.session_manager as session_manager


class SessionManagerTests(unittest.TestCase):
    def test_session_approval_can_be_created_and_checked(self):
        temp_dir = mkdtemp(dir=r"D:\HeyGoku")
        with patch.object(session_manager, "SESSION_FILE", Path(temp_dir) / "sessions.json"):
            session_manager.approve_action("abc", "file_write", minutes=5)
            self.assertTrue(session_manager.is_action_approved("abc", "file_write"))
            session_manager.revoke_action("abc", "file_write")
            self.assertFalse(session_manager.is_action_approved("abc", "file_write"))


if __name__ == "__main__":
    unittest.main()
