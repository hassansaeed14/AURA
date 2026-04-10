import unittest
from unittest.mock import patch

from security.auth_manager import get_auth_state, validate_login


class AuthManagerTests(unittest.TestCase):
    def test_get_auth_state_returns_authenticated_user_when_found(self):
        with patch("security.auth_manager.get_user", return_value={"username": "beast"}):
            result = get_auth_state("beast")
        self.assertTrue(result["authenticated"])
        self.assertEqual(result["user"]["username"], "beast")

    def test_validate_login_surfaces_failed_login_reason(self):
        with patch("security.auth_manager.login_user", return_value=(False, "Wrong password.")):
            result = validate_login("beast", "wrong")
        self.assertFalse(result["success"])
        self.assertEqual(result["reason"], "Wrong password.")


if __name__ == "__main__":
    unittest.main()
