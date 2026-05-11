import importlib
import os
import tempfile
import unittest
from datetime import datetime, timedelta


class AuthRoutesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.temp_dir.name, "test.db")
        os.environ["YGGDRASIL_DATABASE_URI"] = f"sqlite:///{cls.db_path}"
        cls.app_module = importlib.import_module("app")

    @classmethod
    def tearDownClass(cls):
        with cls.app_module.app.app_context():
            cls.app_module.db.session.remove()
            cls.app_module.db.engine.dispose()
        cls.temp_dir.cleanup()
        os.environ.pop("YGGDRASIL_DATABASE_URI", None)

    def setUp(self):
        self.app = self.app_module.app
        self.app.config["TESTING"] = True
        self.app.config["UPLOAD_FOLDER"] = os.path.join(self.temp_dir.name, "uploads")
        self.client = self.app.test_client()
        os.makedirs(os.path.join(self.app.config["UPLOAD_FOLDER"], "wps"), exist_ok=True)
        with self.app.app_context():
            self.app_module.db.drop_all()
            self.app_module.db.create_all()
            self.app_module.ensure_default_records()

    def login_admin(self):
        response = self.client.post(
            "/api/login",
            json={"username": "admin", "password": "123456"},
        )
        self.assertEqual(response.status_code, 200)
        return response.get_json()["token"]

    def register_member(self, username="member", password="pass"):
        response = self.client.post(
            "/api/register",
            json={"username": username, "password": password, "inviteCode": "xjxy666"},
        )
        self.assertEqual(response.status_code, 201)
        with self.app.app_context():
            return self.app_module.User.query.filter_by(username=username).first()

    def test_database_uri_can_be_overridden_for_tests(self):
        self.assertEqual(
            self.app.config["SQLALCHEMY_DATABASE_URI"],
            f"sqlite:///{self.db_path}",
        )

    def test_default_admin_login_returns_admin_role_and_hashes_password(self):
        response = self.client.post(
            "/api/login",
            json={"username": "admin", "password": "123456"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["role"], "admin")
        self.assertIn("token_expires_at", data)

        with self.app.app_context():
            admin = self.app_module.User.query.filter_by(username="admin").first()
            self.assertTrue(admin.is_admin)
            self.assertNotEqual(admin.password, "123456")
            self.assertIsNotNone(admin.token_expires_at)

    def test_expired_token_is_rejected_and_cleared(self):
        admin_token = self.login_admin()

        with self.app.app_context():
            admin = self.app_module.User.query.filter_by(username="admin").first()
            admin.token_expires_at = datetime.utcnow() - timedelta(seconds=1)
            self.app_module.db.session.commit()

        response = self.client.get(
            "/api/admin/overview",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "Token expired")
        with self.app.app_context():
            admin = self.app_module.User.query.filter_by(username="admin").first()
            self.assertIsNone(admin.token)
            self.assertIsNone(admin.token_expires_at)

    def test_registration_requires_valid_backend_invite_code(self):
        bad_response = self.client.post(
            "/api/register",
            json={"username": "alice", "password": "pass", "inviteCode": "bad"},
        )
        good_response = self.client.post(
            "/api/register",
            json={"username": "alice", "password": "pass", "inviteCode": "xjxy666"},
        )

        self.assertEqual(bad_response.status_code, 403)
        self.assertEqual(good_response.status_code, 201)

        with self.app.app_context():
            user = self.app_module.User.query.filter_by(username="alice").first()
            invite = self.app_module.InviteCode.query.filter_by(code="xjxy666").first()
            self.assertIsNotNone(user)
            self.assertEqual(user.role, "member")
            self.assertTrue(user.check_password("pass"))
            self.assertEqual(invite.used_count, 1)

    def test_admin_overview_and_users_require_admin_role(self):
        admin_token = self.login_admin()
        self.register_member("bob", "pass")
        member_login = self.client.post(
            "/api/login",
            json={"username": "bob", "password": "pass"},
        )
        member_token = member_login.get_json()["token"]

        denied = self.client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        overview = self.client.get(
            "/api/admin/overview",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        users = self.client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(overview.status_code, 200)
        self.assertGreaterEqual(overview.get_json()["users"], 2)
        self.assertEqual(users.status_code, 200)
        self.assertIn("admin", [user["username"] for user in users.get_json()])

    def test_admin_can_create_invite_code(self):
        admin_token = self.login_admin()

        created = self.client.post(
            "/api/admin/invite-codes",
            json={"code": "NEXT2026", "max_uses": 2, "note": "next team"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        listing = self.client.get(
            "/api/admin/invite-codes",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(created.status_code, 201)
        self.assertIn("NEXT2026", [item["code"] for item in listing.get_json()])

    def test_admin_can_disable_user(self):
        admin_token = self.login_admin()
        user = self.register_member("carol", "pass")

        response = self.client.patch(
            f"/api/admin/users/{user.id}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        login = self.client.post(
            "/api/login",
            json={"username": "carol", "password": "pass"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(login.status_code, 403)

    def test_admin_cannot_demote_self_to_member(self):
        admin_token = self.login_admin()
        with self.app.app_context():
            admin = self.app_module.User.query.filter_by(username="admin").first()
            admin_id = admin.id

        response = self.client.patch(
            f"/api/admin/users/{admin_id}",
            json={"role": "member"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        users = self.client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Cannot change your own admin role")
        self.assertEqual(users.status_code, 200)
        admin_data = next(user for user in users.get_json() if user["username"] == "admin")
        self.assertEqual(admin_data["role"], "admin")

    def test_admin_can_change_own_password(self):
        admin_token = self.login_admin()

        response = self.client.post(
            "/api/admin/change-password",
            json={"current_password": "123456", "new_password": "NewPass123"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        old_login = self.client.post(
            "/api/login",
            json={"username": "admin", "password": "123456"},
        )
        new_login = self.client.post(
            "/api/login",
            json={"username": "admin", "password": "NewPass123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(old_login.status_code, 401)
        self.assertEqual(new_login.status_code, 200)

    def test_admin_can_list_and_archive_competitions(self):
        admin_token = self.login_admin()
        created = self.client.post(
            "/api/competitions",
            json={"name": "Final Round"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        comp_id = created.get_json()["id"]

        archived = self.client.patch(
            f"/api/admin/competitions/{comp_id}",
            json={"is_archived": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        listing = self.client.get(
            "/api/admin/competitions",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(archived.status_code, 200)
        self.assertTrue(archived.get_json()["is_archived"])
        self.assertIn("Final Round", [item["name"] for item in listing.get_json()])

    def test_admin_can_scan_storage_for_orphan_files(self):
        admin_token = self.login_admin()
        upload_dir = os.path.join(self.app.config["UPLOAD_FOLDER"], "wps")
        os.makedirs(upload_dir, exist_ok=True)
        orphan_path = os.path.join(upload_dir, "orphan.txt")
        with open(orphan_path, "w", encoding="utf-8") as fh:
            fh.write("orphan")

        response = self.client.get(
            "/api/admin/storage",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("orphan.txt", [item["filename"] for item in data["orphans"]])

    def test_admin_can_download_storage_file(self):
        admin_token = self.login_admin()
        upload_dir = os.path.join(self.app.config["UPLOAD_FOLDER"], "wps")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, "evidence.txt")
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write("download me")

        response = self.client.get(
            "/api/admin/storage/files/evidence.txt",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"download me")
        self.assertIn("attachment", response.headers.get("Content-Disposition", ""))
        response.close()

    def test_admin_can_download_database_backup(self):
        admin_token = self.login_admin()

        response = self.client.get(
            "/api/admin/backup/database",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers.get("Content-Disposition", ""))
        response.close()


if __name__ == "__main__":
    unittest.main()
