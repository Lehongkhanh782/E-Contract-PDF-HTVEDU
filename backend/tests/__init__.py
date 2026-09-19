"""Thiết lập chung cho kiểm thử.

Các biến môi trường phải được đặt ở đây, trước khi bất kỳ module test nào
nạp app.main. Ứng dụng đọc cấu hình cookie và khóa ký phiên ngay lúc nạp,
nên đặt muộn hơn sẽ không có tác dụng: cookie vẫn ở chế độ chỉ gửi qua
HTTPS và TestClient chạy HTTP sẽ bỏ cookie đi.
"""
from __future__ import annotations

import atexit
import json
import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.auth import hash_password  # noqa: E402

MAT_KHAU = "matkhauthunghiem123"
MAT_KHAU_KHAC = "matkhaukhacnhau456"

_folder = tempfile.TemporaryDirectory(prefix="econtract_tests_")
atexit.register(_folder.cleanup)

USERS_FILE = Path(_folder.name) / "users.json"
_salt_a, _hash_a = hash_password(MAT_KHAU)
_salt_b, _hash_b = hash_password(MAT_KHAU_KHAC)
USERS_FILE.write_text(
    json.dumps(
        {
            "users": [
                {
                    "username": "nhansu",
                    "display_name": "Phòng Nhân sự",
                    "salt": _salt_a,
                    "hash": _hash_a,
                    "units": ["*"],
                },
                {
                    "username": "vic",
                    "display_name": "Quản lý Victoria",
                    "salt": _salt_b,
                    "hash": _hash_b,
                    "units": ["victoria"],
                },
            ]
        },
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

os.environ["ECONTRACT_USERS_FILE"] = str(USERS_FILE)
os.environ["ECONTRACT_SECRET_KEY"] = "k" * 48
os.environ["ECONTRACT_INSECURE_COOKIES"] = "1"


def sample_request(unit_id: str | None = None) -> dict:
    """Hồ sơ giả của contract_kit, đưa về định dạng của API."""
    from app.config import KIT_DIR

    data = json.loads(
        (KIT_DIR / "examples/employee_demo.json").read_text(encoding="utf-8")
    )
    for key in ("schema_version", "demo_only", "assumptions"):
        data.pop(key, None)
    if unit_id:
        data["unit_id"] = unit_id
    return data


def logged_in_client(username: str = "nhansu", password: str = MAT_KHAU):
    """TestClient đã đăng nhập sẵn."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return client
