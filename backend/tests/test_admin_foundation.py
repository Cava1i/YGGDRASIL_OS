import unittest
from datetime import datetime, timedelta

from models import InviteCode, User


class AdminFoundationTest(unittest.TestCase):
    def test_user_password_is_hashed_and_verified(self):
        user = User(username="captain")

        user.set_password("secret-pass")

        self.assertNotEqual(user.password, "secret-pass")
        self.assertTrue(user.password.startswith("scrypt:") or user.password.startswith("pbkdf2:"))
        self.assertTrue(user.check_password("secret-pass"))
        self.assertFalse(user.check_password("wrong-pass"))

    def test_legacy_plaintext_password_can_still_be_verified(self):
        user = User(username="legacy", password="old-pass")

        self.assertTrue(user.check_password("old-pass"))
        self.assertFalse(user.check_password("wrong-pass"))

    def test_is_admin_requires_admin_role_and_active_user(self):
        admin = User(username="admin", role="admin", is_active=True)
        disabled_admin = User(username="disabled", role="admin", is_active=False)
        member = User(username="member", role="member", is_active=True)

        self.assertTrue(admin.is_admin)
        self.assertFalse(disabled_admin.is_admin)
        self.assertFalse(member.is_admin)

    def test_invite_code_validity_respects_enabled_expiry_and_usage(self):
        valid = InviteCode(code="TEAM2026", is_enabled=True, max_uses=3, used_count=1)
        disabled = InviteCode(code="OFF", is_enabled=False)
        expired = InviteCode(
            code="OLD",
            is_enabled=True,
            expires_at=datetime.utcnow() - timedelta(days=1),
        )
        exhausted = InviteCode(code="FULL", is_enabled=True, max_uses=2, used_count=2)

        self.assertTrue(valid.is_valid())
        self.assertFalse(disabled.is_valid())
        self.assertFalse(expired.is_valid())
        self.assertFalse(exhausted.is_valid())


if __name__ == "__main__":
    unittest.main()
