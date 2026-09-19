"""Đăng nhập, đăng xuất và xem tài khoản hiện tại."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app import config
from app.auth import User
from app.deps import SESSION_KEY, current_user, store

router = APIRouter(prefix="/api")


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/login")
def login(request: Request, body: LoginRequest) -> dict:
    users = store()
    if not users.configured:
        raise HTTPException(
            status_code=503,
            detail=(
                "Máy chủ chưa có tài khoản nào. Chạy lệnh "
                "python -m app.usertool them <tên tài khoản> để tạo."
            ),
        )

    user, locked_for = users.authenticate(body.username, body.password,
                                          _client_key(request))
    if locked_for:
        raise HTTPException(
            status_code=429,
            detail=f"Sai quá nhiều lần. Thử lại sau {locked_for // 60 + 1} phút.",
        )
    if user is None:
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")

    # Cấp id phiên mới sau khi đăng nhập để tránh dùng lại phiên cũ.
    request.session.clear()
    request.session[SESSION_KEY] = user.username
    return _describe(user)


@router.post("/logout")
def logout(request: Request) -> dict:
    request.session.clear()
    return {"status": "da_dang_xuat"}


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return _describe(user)


def _describe(user: User) -> dict:
    configured = [unit["unit_id"] for unit in config.units()]
    return {
        "username": user.username,
        "display_name": user.display_name,
        "units": user.visible_units(configured),
        "all_units": "*" in user.units,
    }
