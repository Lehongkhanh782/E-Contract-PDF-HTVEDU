"""Ứng dụng FastAPI tạo hợp đồng cho 4 đơn vị.

Bản thử nghiệm: đã có đăng nhập và phân quyền theo cơ sở, chưa có database,
OCR hay luồng phát hành chính thức.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.auth_routes import router as auth_router
from app.api.routes import router
from app.auth import https_only, session_secret

logger = logging.getLogger("econtract")

app = FastAPI(
    title="Tạo hợp đồng lao động - 4 cơ sở",
    description="Bản thử nghiệm. PDF tạo ra mang dấu DỮ LIỆU GIẢ - CHƯA DÙNG KÝ.",
    version="0.2.0",
)

secret, temporary = session_secret()
if temporary:
    logger.warning(
        "Chưa đặt ECONTRACT_SECRET_KEY nên dùng khóa tạm. Mọi người sẽ bị "
        "đăng xuất mỗi lần khởi động lại máy chủ. Sinh khóa cố định bằng "
        "lệnh: python -m app.usertool khoa-bi-mat"
    )

secure_cookies = https_only()
if not secure_cookies:
    logger.warning(
        "Cookie đang cho phép gửi qua HTTP vì ECONTRACT_INSECURE_COOKIES được "
        "bật. Chỉ dùng khi chạy thử trên máy cá nhân, không dùng trên mạng."
    )

app.add_middleware(
    SessionMiddleware,
    secret_key=secret,
    session_cookie="econtract_session",
    https_only=secure_cookies,
    same_site="lax",
    max_age=8 * 60 * 60,  # một ngày làm việc
)

# Khi chạy phát triển, frontend nằm ở cổng khác nên cần cho phép gọi chéo.
# allow_credentials để trình duyệt gửi kèm cookie phiên.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    expose_headers=["Content-Disposition", "X-Demo-Only", "X-Calculation-Sha256"],
)

app.include_router(auth_router)
app.include_router(router)

# Khi đã build frontend, phục vụ luôn file tĩnh từ cùng máy chủ.
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")
