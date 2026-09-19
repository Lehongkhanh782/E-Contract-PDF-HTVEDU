"""Phụ thuộc dùng chung: lấy người dùng đang đăng nhập."""
from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException, Request

from app.auth import User, UserStore

SESSION_KEY = "username"


@lru_cache(maxsize=1)
def store() -> UserStore:
    return UserStore.load()


def current_user(request: Request) -> User:
    """Chặn mọi yêu cầu chưa đăng nhập.

    Nếu tài khoản bị xóa khỏi cấu hình thì phiên cũ cũng hết hiệu lực ngay.
    """
    username = request.session.get(SESSION_KEY)
    if not username:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")
    user = store().get(username)
    if user is None:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không còn hiệu lực")
    return user


def require_unit(user: User, unit_id: str) -> None:
    """Kiểm tra lại ở phía máy chủ, không tin giá trị do trình duyệt gửi."""
    if not user.may_use(unit_id):
        raise HTTPException(
            status_code=403,
            detail="Tài khoản không có quyền với cơ sở này",
        )
