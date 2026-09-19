"""Tài khoản, mật khẩu và phạm vi đơn vị.

Mật khẩu được băm bằng scrypt của thư viện chuẩn Python, có muối riêng cho
từng tài khoản. File lưu tài khoản không bao giờ chứa mật khẩu gốc.

Bản này chưa dùng database. Danh sách tài khoản đọc từ biến môi trường
ECONTRACT_USERS hoặc từ file mà ECONTRACT_USERS_FILE trỏ tới. Cách này đủ
cho một nhóm nhân sự nhỏ và chạy được trên các nền tảng không có ổ đĩa lưu
lâu dài. Khi cần nhiều người dùng và lịch sử thao tác thì chuyển sang
database theo bản đặc tả.
"""
from __future__ import annotations

import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from hashlib import scrypt
from pathlib import Path
from threading import Lock

# Tham số scrypt. Đổi các số này sẽ làm mọi mật khẩu đã băm không dùng được.
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
DK_LEN = 32
SALT_BYTES = 16

# Chặn dò mật khẩu: sai quá số lần thì khóa tạm.
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300

ALL_UNITS = "*"


@dataclass(frozen=True)
class User:
    username: str
    display_name: str
    units: tuple[str, ...]

    def may_use(self, unit_id: str) -> bool:
        return ALL_UNITS in self.units or unit_id in self.units

    def visible_units(self, configured: list[str]) -> list[str]:
        if ALL_UNITS in self.units:
            return list(configured)
        return [unit for unit in configured if unit in self.units]


def hash_password(password: str) -> tuple[str, str]:
    """Trả về (muối, mã băm) dạng chuỗi hex."""
    if len(password) < 10:
        raise ValueError("Mật khẩu phải dài ít nhất 10 ký tự")
    salt = secrets.token_bytes(SALT_BYTES)
    digest = scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N,
                    r=SCRYPT_R, p=SCRYPT_P, dklen=DK_LEN)
    return salt.hex(), digest.hex()


def _verify(password: str, salt_hex: str, hash_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    digest = scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N,
                    r=SCRYPT_R, p=SCRYPT_P, dklen=DK_LEN)
    return hmac.compare_digest(digest, expected)


@dataclass
class _Record:
    username: str
    display_name: str
    salt: str
    hash: str
    units: tuple[str, ...]


class UserStore:
    """Danh sách tài khoản, kèm bộ đếm lần đăng nhập sai."""

    def __init__(self, records: dict[str, _Record]) -> None:
        self._records = records
        self._failures: dict[str, list[float]] = {}
        self._lock = Lock()

    @property
    def configured(self) -> bool:
        return bool(self._records)

    @classmethod
    def load(cls) -> "UserStore":
        raw = os.environ.get("ECONTRACT_USERS")
        if not raw:
            path = os.environ.get("ECONTRACT_USERS_FILE")
            candidate = Path(path) if path else Path("users.json")
            if candidate.is_file():
                raw = candidate.read_text(encoding="utf-8")
        if not raw:
            return cls({})

        data = json.loads(raw)
        records: dict[str, _Record] = {}
        for entry in data.get("users", []):
            username = str(entry["username"]).strip().lower()
            if not username:
                raise ValueError("Tài khoản không được để trống")
            if username in records:
                raise ValueError(f"Tài khoản {username} bị khai trùng")
            units = tuple(entry.get("units") or ())
            if not units:
                raise ValueError(f"Tài khoản {username} chưa được gán đơn vị nào")
            records[username] = _Record(
                username=username,
                display_name=str(entry.get("display_name") or username),
                salt=str(entry["salt"]),
                hash=str(entry["hash"]),
                units=units,
            )
        return cls(records)

    def _locked_for(self, key: str) -> int:
        """Số giây còn bị khóa. 0 nghĩa là không bị khóa."""
        now = time.monotonic()
        recent = [t for t in self._failures.get(key, []) if now - t < LOCKOUT_SECONDS]
        self._failures[key] = recent
        if len(recent) < MAX_ATTEMPTS:
            return 0
        return int(LOCKOUT_SECONDS - (now - recent[0])) + 1

    def authenticate(self, username: str, password: str, client: str
                     ) -> tuple[User | None, int]:
        """Trả về (người dùng, số giây bị khóa).

        Sai tài khoản và sai mật khẩu cho cùng một kết quả để người ngoài
        không dò được tài khoản nào có thật.
        """
        key = f"{client}|{username.strip().lower()}"
        with self._lock:
            remaining = self._locked_for(key)
            if remaining:
                return None, remaining

        record = self._records.get(username.strip().lower())
        if record is None:
            # Vẫn băm một lần để thời gian phản hồi không tố cáo tài khoản
            # nào tồn tại.
            _verify(password, secrets.token_bytes(SALT_BYTES).hex(), "00" * DK_LEN)
            ok = False
        else:
            ok = _verify(password, record.salt, record.hash)

        with self._lock:
            if ok:
                self._failures.pop(key, None)
            else:
                self._failures.setdefault(key, []).append(time.monotonic())
        if not ok or record is None:
            return None, 0
        return User(record.username, record.display_name, record.units), 0

    def get(self, username: str) -> User | None:
        record = self._records.get(username.strip().lower())
        if record is None:
            return None
        return User(record.username, record.display_name, record.units)


def session_secret() -> tuple[str, bool]:
    """Khóa ký cookie phiên. Trả về (khóa, có phải khóa tạm không)."""
    configured = os.environ.get("ECONTRACT_SECRET_KEY", "").strip()
    if configured:
        if len(configured) < 32:
            raise ValueError("ECONTRACT_SECRET_KEY phải dài ít nhất 32 ký tự")
        return configured, False
    # Không có khóa cố định thì sinh tạm; mọi người sẽ bị đăng xuất mỗi lần
    # khởi động lại máy chủ.
    return secrets.token_urlsafe(48), True


def https_only() -> bool:
    """Cookie chỉ gửi qua HTTPS. Tắt khi chạy thử trên máy cá nhân."""
    return os.environ.get("ECONTRACT_INSECURE_COOKIES", "").strip().lower() not in {
        "1", "true", "yes",
    }
