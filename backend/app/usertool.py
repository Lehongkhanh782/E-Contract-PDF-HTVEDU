"""Công cụ dòng lệnh tạo và sửa tài khoản.

    python -m app.usertool them nhansu
    python -m app.usertool them hieutruong-vic --don-vi victoria
    python -m app.usertool doi-mat-khau nhansu
    python -m app.usertool xem
    python -m app.usertool xuat
    python -m app.usertool khoa-bi-mat

Công cụ này chỉ dùng thư viện chuẩn của Python, không cần cài gì thêm.

Mật khẩu được gõ ẩn, không hiện lên màn hình và không nằm trong lịch sử
lệnh. File users.json chỉ chứa mã băm, không chứa mật khẩu gốc.
"""
from __future__ import annotations

import argparse
import getpass
import json
import secrets
import sys
from pathlib import Path

from app import config
from app.auth import ALL_UNITS, hash_password

DEFAULT_FILE = Path("users.json")


def _read(path: Path) -> dict:
    if not path.is_file():
        return {"users": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    # Chỉ chủ sở hữu file được đọc.
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _ask_password() -> str:
    first = getpass.getpass("Mật khẩu mới (ít nhất 10 ký tự, gõ không hiện): ")
    if len(first) < 10:
        sys.exit("Mật khẩu quá ngắn. Cần ít nhất 10 ký tự.")
    if first != getpass.getpass("Gõ lại mật khẩu: "):
        sys.exit("Hai lần gõ không giống nhau.")
    return first


def _check_units(values: list[str]) -> tuple[str, ...]:
    if not values or values == ["tat-ca"]:
        return (ALL_UNITS,)
    known = {unit["unit_id"] for unit in config.units()}
    unknown = [value for value in values if value not in known]
    if unknown:
        sys.exit(
            f"Không có đơn vị: {', '.join(unknown)}.\n"
            f"Các đơn vị hợp lệ: {', '.join(sorted(known))}"
        )
    return tuple(values)


def command_add(args: argparse.Namespace) -> None:
    path = Path(args.file)
    data = _read(path)
    username = args.username.strip().lower()
    if any(user["username"] == username for user in data["users"]):
        sys.exit(f"Tài khoản {username} đã tồn tại. Dùng lệnh doi-mat-khau.")
    units = _check_units(args.don_vi)
    salt, digest = hash_password(_ask_password())
    data["users"].append({
        "username": username,
        "display_name": args.ten_hien_thi or username,
        "salt": salt,
        "hash": digest,
        "units": list(units),
    })
    _write(path, data)
    scope = "tất cả 4 cơ sở" if units == (ALL_UNITS,) else ", ".join(units)
    print(f"Đã tạo tài khoản {username}, phạm vi: {scope}")
    print(f"File tài khoản: {path.resolve()}")


def command_passwd(args: argparse.Namespace) -> None:
    path = Path(args.file)
    data = _read(path)
    username = args.username.strip().lower()
    for user in data["users"]:
        if user["username"] == username:
            user["salt"], user["hash"] = hash_password(_ask_password())
            _write(path, data)
            print(f"Đã đổi mật khẩu cho {username}")
            return
    sys.exit(f"Không có tài khoản {username}")


def command_list(args: argparse.Namespace) -> None:
    data = _read(Path(args.file))
    if not data["users"]:
        print("Chưa có tài khoản nào.")
        return
    for user in data["users"]:
        units = user["units"]
        scope = "tất cả 4 cơ sở" if ALL_UNITS in units else ", ".join(units)
        print(f"{user['username']:<20} {user.get('display_name', ''):<28} {scope}")


def command_export(args: argparse.Namespace) -> None:
    """In danh sách tài khoản trên MỘT dòng để dán vào ECONTRACT_USERS."""
    path = Path(args.file)
    if not path.is_file():
        sys.exit(f"Chưa có file {path}. Tạo tài khoản trước bằng lệnh them.")
    data = _read(path)
    if not data["users"]:
        sys.exit("Chưa có tài khoản nào.")
    print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def command_secret(_: argparse.Namespace) -> None:
    print("Đặt biến môi trường này trên máy chủ để không bị đăng xuất khi khởi động lại:")
    print()
    print(f"ECONTRACT_SECRET_KEY={secrets.token_urlsafe(48)}")
    print()
    print("Giữ kín chuỗi trên. Không đưa vào Git, không gửi qua chat.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", default=str(DEFAULT_FILE),
                        help="Đường dẫn file tài khoản (mặc định users.json)")
    sub = parser.add_subparsers(dest="lenh", required=True)

    add = sub.add_parser("them", help="Tạo tài khoản mới")
    add.add_argument("username")
    add.add_argument("--ten-hien-thi", default=None)
    add.add_argument("--don-vi", nargs="*", default=[],
                     help="Mã đơn vị được phép; bỏ trống là tất cả")
    add.set_defaults(func=command_add)

    passwd = sub.add_parser("doi-mat-khau", help="Đổi mật khẩu")
    passwd.add_argument("username")
    passwd.set_defaults(func=command_passwd)

    listing = sub.add_parser("xem", help="Xem danh sách tài khoản")
    listing.set_defaults(func=command_list)

    export = sub.add_parser(
        "xuat", help="In một dòng JSON để dán vào biến ECONTRACT_USERS")
    export.set_defaults(func=command_export)

    secret = sub.add_parser("khoa-bi-mat", help="Sinh khóa ký phiên đăng nhập")
    secret.set_defaults(func=command_secret)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
