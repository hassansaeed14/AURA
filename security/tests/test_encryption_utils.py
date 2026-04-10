import unittest

from security.encryption_utils import generate_token, hash_secret, verify_secret


class EncryptionUtilsTests(unittest.TestCase):
    def test_hash_and_verify_secret_round_trip(self):
        hashed = hash_secret("Jarvis1234")
        self.assertTrue(verify_secret("Jarvis1234", hashed))
        self.assertFalse(verify_secret("WrongSecret", hashed))

    def test_generate_token_returns_non_empty_string(self):
        token = generate_token()
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 10)


if __name__ == "__main__":
    unittest.main()
