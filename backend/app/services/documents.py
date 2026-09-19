"""Gọi lại phần lõi contract_kit để tính lương và tạo PDF.

Chỉ tạo tài liệu thử nghiệm. Chưa có chế độ phát hành chính thức, đánh số
hợp đồng, snapshot hay luồng duyệt; các phần đó theo bản đặc tả.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path

from app.config import KIT_DIR, TEMPLATE_DIR, salary_policy

# Import sau config vì config đã thêm contract_kit vào sys.path.
from generate_demo import (  # noqa: E402  (phụ thuộc thứ tự sys.path)
    build_context,
    convert_to_pdf,
    merge_demo_pdf,
    page_count_label,
    render_docx,
)

# Font cho dòng đánh dấu bản thử nghiệm in lên mỗi trang PDF. Đặt biến
# ECONTRACT_DEMO_FONT để dùng font khác, ví dụ khi chạy trên Windows.
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "C:/Windows/Fonts/arial.ttf",
)
MAX_PAGE_PASSES = 3


def _soffice() -> str:
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if not found:
        raise RuntimeError(
            "Chưa cài LibreOffice trên máy chủ. Cần cả gói libreoffice-writer "
            "thì mới mở được file Word."
        )
    return found


def _font() -> Path:
    configured = os.environ.get("ECONTRACT_DEMO_FONT", "").strip()
    if configured:
        path = Path(configured)
        if not path.is_file():
            raise RuntimeError(
                f"ECONTRACT_DEMO_FONT trỏ tới {path} nhưng không có file đó."
            )
        return path
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if path.is_file():
            return path
    raise RuntimeError(
        "Không tìm thấy font cho dòng đánh dấu bản thử nghiệm. Cài gói "
        "fonts-dejavu-core, hoặc đặt biến ECONTRACT_DEMO_FONT trỏ tới một "
        "file .ttf có hỗ trợ tiếng Việt."
    )


def calculate(unit_id: str, payload: dict) -> dict:
    """Chỉ tính tiền, không tạo file. Dùng cho màn hình xem trước."""
    _, result = build_context(unit_id, payload, salary_policy())
    return result


def build_pdf(unit_id: str, payload: dict, destination: Path) -> dict:
    """Tạo một PDF gồm hợp đồng, phụ lục lương và thỏa thuận trách nhiệm."""
    from pypdf import PdfReader

    soffice = _soffice()
    font = _font()
    context, result = build_context(unit_id, payload, salary_policy())

    contract_template = TEMPLATE_DIR / "Hop_dong_va_phu_luc_template.docx"
    agreement_template = TEMPLATE_DIR / "Thoa_thuan_trach_nhiem_template.docx"

    with tempfile.TemporaryDirectory(prefix="econtract_") as folder:
        work = Path(folder)
        contract_docx = work / "DEMO_Hop_dong_va_phu_luc.docx"
        agreement_docx = work / "DEMO_Thoa_thuan.docx"

        render_docx(contract_template, contract_docx, context)
        contract_pdf = convert_to_pdf(contract_docx, work / "pdf", soffice)

        # Số trang thỏa thuận được in trong chính văn bản, nên phải render lại
        # cho tới khi con số điền vào khớp số trang thật.
        for _ in range(MAX_PAGE_PASSES):
            render_docx(agreement_template, agreement_docx, context)
            agreement_pdf = convert_to_pdf(agreement_docx, work / "pdf", soffice)
            actual = len(PdfReader(agreement_pdf).pages)
            if context["responsibility"]["page_count_label"] == page_count_label(actual):
                break
            context["responsibility"]["page_count_label"] = page_count_label(actual)
        else:
            raise RuntimeError("Số trang thỏa thuận chưa ổn định sau nhiều lần dựng")

        merge_demo_pdf([contract_pdf, agreement_pdf], destination, font)

    return {
        "demo_only": True,
        "unit_id": unit_id,
        "calculation": result,
        "position_id": payload["job"]["position_id"],
        "salary_mode": payload["compensation"]["salary_mode"],
        "salary_amount": payload["compensation"]["salary_amount"],
        "signing_and_effective_date": payload["signing_date"],
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "policy_status": salary_policy()["status"],
    }


__all__ = ["calculate", "build_pdf", "KIT_DIR"]
