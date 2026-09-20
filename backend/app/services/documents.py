"""Gọi lại phần lõi contract_kit để tính lương và tạo PDF.

Chỉ tạo tài liệu thử nghiệm. Chưa có chế độ phát hành chính thức, đánh số
hợp đồng, snapshot hay luồng duyệt; các phần đó theo bản đặc tả.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import threading
from pathlib import Path

from app.config import KIT_DIR, TEMPLATE_DIR, salary_policy

# Import sau config vì config đã thêm contract_kit vào sys.path.
from generate_demo import (  # noqa: E402  (phụ thuộc thứ tự sys.path)
    ban_thu_nghiem,
    build_context,
    build_probation_context,
    can_thoa_thuan,
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

# Mỗi lần dựng PDF, LibreOffice chiếm khoảng 240 MB trên máy đã đo, tổng
# tiến trình lên đỉnh khoảng 300 MB. Chạy hai lần cùng lúc trên máy chủ
# 512 MB sẽ hết bộ nhớ và bị buộc dừng. Vì vậy xếp hàng thay vì chạy song
# song: chậm hơn một chút nhưng không bao giờ đổ.
#
# Máy chủ nhiều bộ nhớ hơn có thể nâng lên bằng ECONTRACT_MAX_PDF_SONG_SONG.
# Cần khoảng 300 MB cho mỗi luồng, cộng thêm 100 MB cho phần còn lại.
def _max_song_song() -> int:
    raw = os.environ.get("ECONTRACT_MAX_PDF_SONG_SONG", "1").strip()
    try:
        value = int(raw)
    except ValueError:
        return 1
    return max(1, value)


_cong_pdf = threading.BoundedSemaphore(_max_song_song())

# Chờ tối đa bấy nhiêu giây đến lượt mình. Quá thì báo bận thay vì để người
# dùng ngồi nhìn màn hình quay mãi.
THOI_GIAN_CHO_LUOT = 90


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


def tinh_luong(position_id: str, compensation: dict) -> dict:
    """Tính lương mà không cần hồ sơ đầy đủ.

    Dùng cho bảng lương hiện ngay khi nhân sự gõ ở mục Lương, trước khi
    điền xong các phần khác. Vẫn đi qua đúng bộ tính của phần lõi nên
    không có công thức thứ hai nào tồn tại song song.
    """
    from generate_demo import calculate_example

    ket_qua = calculate_example(
        {"job": {"position_id": position_id}, "compensation": compensation},
        salary_policy(),
    )
    return {key: str(value) for key, value in ket_qua.items()}


def build_pdf(unit_id: str, payload: dict, destination: Path) -> dict:
    """Tạo một PDF gồm hợp đồng, phụ lục lương và thỏa thuận trách nhiệm.

    Chỉ một lượt dựng chạy tại một thời điểm, trừ khi cấu hình khác đi.
    """
    if not _cong_pdf.acquire(timeout=THOI_GIAN_CHO_LUOT):
        raise RuntimeError(
            "Máy chủ đang bận dựng hồ sơ khác. Chờ một lát rồi bấm lại."
        )
    try:
        return _build_pdf(unit_id, payload, destination)
    finally:
        _cong_pdf.release()


def build_probation_pdf(unit_id: str, payload: dict, destination: Path) -> dict:
    """Tạo PDF hợp đồng thử việc: một tờ, không phụ lục, không thỏa thuận."""
    if not _cong_pdf.acquire(timeout=THOI_GIAN_CHO_LUOT):
        raise RuntimeError(
            "Máy chủ đang bận dựng hồ sơ khác. Chờ một lát rồi bấm lại."
        )
    try:
        return _build_probation_pdf(unit_id, payload, destination)
    finally:
        _cong_pdf.release()


def _build_probation_pdf(unit_id: str, payload: dict, destination: Path) -> dict:
    soffice = _soffice()
    font = _font()
    context, result = build_probation_context(unit_id, payload)
    template = TEMPLATE_DIR / "Hop_dong_thu_viec_template.docx"

    with tempfile.TemporaryDirectory(prefix="econtract_") as folder:
        work = Path(folder)
        docx = work / "Hop_dong_thu_viec.docx"
        render_docx(template, docx, context)
        pdf = convert_to_pdf(docx, work / "pdf", soffice)
        # Vẫn đi qua merge để bản thử nghiệm được đóng dấu như mọi bản khác.
        merge_demo_pdf([pdf], destination, font, mot_tap=True)

    return {
        "demo_only": ban_thu_nghiem(),
        "unit_id": unit_id,
        "contract_type": "probation",
        "contract_number": context["contract"]["number"],
        "calculation": result,
        "position_id": payload["job"]["position_id"],
        "signing_and_effective_date": payload["signing_date"],
    }


def _build_pdf(unit_id: str, payload: dict, destination: Path) -> dict:
    from pypdf import PdfReader

    soffice = _soffice()
    font = _font()
    context, result = build_context(unit_id, payload, salary_policy())
    # Chỉ vị trí trực tiếp dạy và trông trẻ mới kèm thỏa thuận trách nhiệm.
    kem_thoa_thuan = can_thoa_thuan(payload)

    contract_template = TEMPLATE_DIR / "Hop_dong_va_phu_luc_template.docx"
    agreement_template = TEMPLATE_DIR / "Thoa_thuan_trach_nhiem_template.docx"

    with tempfile.TemporaryDirectory(prefix="econtract_") as folder:
        work = Path(folder)
        contract_docx = work / "DEMO_Hop_dong_va_phu_luc.docx"
        agreement_docx = work / "DEMO_Thoa_thuan.docx"

        render_docx(contract_template, contract_docx, context)
        contract_pdf = convert_to_pdf(contract_docx, work / "pdf", soffice)
        bo_file = [contract_pdf]

        if kem_thoa_thuan:
            # Số trang thỏa thuận được in trong chính văn bản, nên phải
            # render lại cho tới khi con số điền vào khớp số trang thật.
            for _ in range(MAX_PAGE_PASSES):
                render_docx(agreement_template, agreement_docx, context)
                agreement_pdf = convert_to_pdf(agreement_docx, work / "pdf", soffice)
                actual = len(PdfReader(agreement_pdf).pages)
                if context["responsibility"]["page_count_label"] == page_count_label(actual):
                    break
                context["responsibility"]["page_count_label"] = page_count_label(actual)
            else:
                raise RuntimeError("Số trang thỏa thuận chưa ổn định sau nhiều lần dựng")
            bo_file.append(agreement_pdf)

        merge_demo_pdf(bo_file, destination, font)

    return {
        "demo_only": ban_thu_nghiem(),
        "unit_id": unit_id,
        "calculation": result,
        "position_id": payload["job"]["position_id"],
        "salary_mode": payload["compensation"]["salary_mode"],
        "salary_amount": payload["compensation"]["salary_amount"],
        "signing_and_effective_date": payload["signing_date"],
        "includes_responsibility_agreement": kem_thoa_thuan,
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "policy_status": salary_policy()["status"],
    }


__all__ = ["calculate", "build_pdf", "KIT_DIR"]
