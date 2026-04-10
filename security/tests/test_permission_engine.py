import unittest

from config.permissions_config import get_permission_profile


class PermissionEngineTests(unittest.TestCase):
    def test_permission_profile_maps_trust_level_and_rule(self):
        profile = get_permission_profile("file_delete")
        self.assertEqual(profile.trust_level, "critical")
        self.assertEqual(profile.rule, "pin")


if __name__ == "__main__":
    unittest.main()
