"""Ứng dụng FastAPI tạo hợp đồng cho 4 đơn vị.

Bản thử nghiệm: chưa có đăng nhập, database, OCR hay phát hành chính thức.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router

app = FastAPI(
    title="Tạo hợp đồng lao động - 4 cơ sở",
    description="Bản thử nghiệm. PDF tạo ra mang dấu DỮ LIỆU GIẢ - CHƯA DÙNG KÝ.",
    version="0.1.0",
)

# Khi chạy phát triển, frontend nằm ở cổng khác nên cần cho phép gọi chéo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    expose_headers=["Content-Disposition", "X-Demo-Only", "X-Calculation-Sha256"],
)

app.include_router(router)

# Khi đã build frontend, phục vụ luôn file tĩnh từ cùng máy chủ.
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")
