"""Kiểm thử đăng nhập và phân quyền theo cơ sở."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.auth import UserStore, hash_password
from app.main import app
from tests import MAT_KHAU, MAT_KHAU_KHAC, sample_request


class AuthTestCase(unittest.TestCase):
    """Nền chung: mỗi lớp bắt đầu bằng một phiên trắng.

    Bộ đếm đăng nhập sai nằm trong UserStore, nên phải nạp lại store giữa
    các lớp để lớp thử khóa tài khoản không làm hỏng lớp sau.
    """

    @classmethod
    def setUpClass(cls) -> None:
        from app import deps

        deps.store.cache_clear()
        cls.client = TestClient(app)

    def login(self, username: str, password: str):
        return self.client.post(
            "/api/login", json={"username": username, "password": password}
        )

    def tearDown(self) -> None:
        self.client.cookies.clear()


class TestLoginRequired(AuthTestCase):
    def test_units_blocked_when_not_logged_in(self):
        self.assertEqual(self.client.get("/api/units").status_code, 401)

    def test_positions_blocked_when_not_logged_in(self):
        self.assertEqual(self.client.get("/api/positions").status_code, 401)

    def test_defaults_blocked_when_not_logged_in(self):
        self.assertEqual(self.client.get("/api/defaults").status_code, 401)

    def test_preview_blocked_when_not_logged_in(self):
        response = self.client.post("/api/preview", json={})
        self.assertEqual(response.status_code, 401)

    def test_generate_blocked_when_not_logged_in(self):
        response = self.client.post("/api/generate", json={})
        self.assertEqual(response.status_code, 401)

    def test_me_blocked_when_not_logged_in(self):
        self.assertEqual(self.client.get("/api/me").status_code, 401)

    def test_health_stays_public(self):
        self.assertEqual(self.client.get("/api/health").status_code, 200)


class TestLogin(AuthTestCase):
    def test_correct_password_succeeds(self):
        response = self.login("nhansu", MAT_KHAU)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["display_name"], "Phòng Nhân sự")

    def test_username_is_case_insensitive(self):
        self.assertEqual(self.login("NhanSu", MAT_KHAU).status_code, 200)

    def test_wrong_password_fails(self):
        self.assertEqual(self.login("nhansu", "saibet123456").status_code, 401)

    def test_unknown_user_gives_same_message_as_wrong_password(self):
        unknown = self.login("khongcotaikhoannay", "saibet123456")
        wrong = self.login("nhansu", "saibet123456")
        self.assertEqual(unknown.status_code, wrong.status_code)
        self.assertEqual(unknown.json()["detail"], wrong.json()["detail"])

    def test_session_survives_across_requests(self):
        self.login("nhansu", MAT_KHAU)
        self.assertEqual(self.client.get("/api/me").status_code, 200)

    def test_logout_ends_session(self):
        self.login("nhansu", MAT_KHAU)
        self.assertEqual(self.client.post("/api/logout").status_code, 200)
        self.assertEqual(self.client.get("/api/me").status_code, 401)

    def test_password_never_appears_in_response(self):
        body = self.login("nhansu", MAT_KHAU).text
        self.assertNotIn(MAT_KHAU, body)
        self.assertNotIn("hash", body)
        self.assertNotIn("salt", body)


class TestUnitScope(AuthTestCase):
    def sample(self, unit_id: str) -> dict:
        return sample_request(unit_id)

    def test_full_scope_account_sees_all_four(self):
        self.login("nhansu", MAT_KHAU)
        units = self.client.get("/api/units").json()["units"]
        self.assertEqual(len(units), 4)

    def test_limited_account_sees_only_its_unit(self):
        self.login("vic", MAT_KHAU_KHAC)
        units = self.client.get("/api/units").json()["units"]
        self.assertEqual([unit["unit_id"] for unit in units], ["victoria"])

    def test_limited_account_may_use_its_own_unit(self):
        self.login("vic", MAT_KHAU_KHAC)
        response = self.client.post("/api/preview", json=self.sample("victoria"))
        self.assertEqual(response.status_code, 200, response.text)

    def test_limited_account_blocked_from_other_unit_preview(self):
        """Chặn ở máy chủ, dù trình duyệt có gửi mã đơn vị khác."""
        self.login("vic", MAT_KHAU_KHAC)
        response = self.client.post("/api/preview", json=self.sample("gau_panda"))
        self.assertEqual(response.status_code, 403)

    def test_limited_account_blocked_from_other_unit_generate(self):
        self.login("vic", MAT_KHAU_KHAC)
        response = self.client.post("/api/generate", json=self.sample("dai_duong_xanh"))
        self.assertEqual(response.status_code, 403)

    def test_me_reports_allowed_units_only(self):
        self.login("vic", MAT_KHAU_KHAC)
        body = self.client.get("/api/me").json()
        self.assertEqual(body["units"], ["victoria"])
        self.assertFalse(body["all_units"])


class TestLockout(AuthTestCase):
    def test_account_locks_after_repeated_failures(self):
        for _ in range(5):
            self.login("nhansu", "saibet123456")
        blocked = self.login("nhansu", "saibet123456")
        self.assertEqual(blocked.status_code, 429)

    def test_correct_password_also_blocked_while_locked(self):
        """Khóa phải chặn cả mật khẩu đúng, nếu không thì dò được."""
        for _ in range(5):
            self.login("nhansu", "saibet123456")
        self.assertEqual(self.login("nhansu", MAT_KHAU).status_code, 429)


class TestUserStore(unittest.TestCase):
    def test_account_without_units_is_rejected(self):
        import os

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "users.json"
            salt, digest = hash_password(MAT_KHAU)
            path.write_text(
                json.dumps(
                    {"users": [{"username": "x", "salt": salt,
                                "hash": digest, "units": []}]}
                ),
                encoding="utf-8",
            )
            os.environ["ECONTRACT_USERS_FILE"] = str(path)
            with self.assertRaises(ValueError):
                UserStore.load()

    def test_duplicate_usernames_are_rejected(self):
        import os

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "users.json"
            salt, digest = hash_password(MAT_KHAU)
            entry = {"username": "x", "salt": salt, "hash": digest, "units": ["*"]}
            path.write_text(json.dumps({"users": [entry, dict(entry)]}),
                            encoding="utf-8")
            os.environ["ECONTRACT_USERS_FILE"] = str(path)
            with self.assertRaises(ValueError):
                UserStore.load()

    def test_short_password_is_refused(self):
        with self.assertRaises(ValueError):
            hash_password("ngan")


if __name__ == "__main__":
    unittest.main()
