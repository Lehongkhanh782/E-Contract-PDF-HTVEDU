"""Đọc danh sách nhân viên từ Google Sheet dùng chung với ứng dụng nhân sự.

Dùng tài khoản máy của Google: máy chủ tự lấy vé vào cửa bằng khóa JSON,
không cần ai đăng nhập bằng tay. Gọi thẳng REST API bằng httpx thay vì thư
viện google-api-python-client, vì thư viện đó nặng 20 MB còn cách này chỉ
thêm 524 KB — đáng kể trên máy chủ 512 MB.

Chưa cấu hình khóa thì toàn bộ chức năng này tự tắt, ứng dụng vẫn chạy
bình thường như trước.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import unicodedata
from typing import Any

PHAM_VI = "https://www.googleapis.com/auth/spreadsheets"
GOC_API = "https://sheets.googleapis.com/v4/spreadsheets"

# Đọc lại Sheet nhiều nhất mỗi ngần này giây, để không chạm hạn mức của
# Google và để mở form nhanh hơn.
THOI_GIAN_NHO = 60
THOI_GIAN_CHO = 20
SO_DONG_TOI_DA = 5000


class ChuaCauHinh(RuntimeError):
    """Chưa khai khóa hoặc mã Sheet."""


class LoiSheet(RuntimeError):
    """Gọi Google Sheets không thành công."""


# Tên cột có thể gặp, viết không dấu và viết thường. Cột nào khớp nhiều
# chữ nhất sẽ được chọn, nên "ngày cấp" không bị nhầm sang "ngày sinh".
TEN_COT = {
    "code": ("ma nhan vien", "ma nv", "ma so nhan vien", "employee code",
             "ma nhan su", "employee id", "ma so"),
    "full_name": ("ho va ten", "ho ten", "ten nhan vien", "full name",
                  "ho, chu dem va ten", "name"),
    "birth_date": ("ngay sinh", "ngay thang nam sinh", "date of birth", "dob"),
    "gender": ("gioi tinh", "sex", "gender"),
    "nationality": ("quoc tich", "nationality"),
    "identity_number": ("so cccd", "cccd", "cmnd", "so can cuoc",
                        "so giay to", "so dinh danh", "identity number"),
    "identity_issue_date": ("ngay cap", "date of issue"),
    "identity_issuer": ("noi cap", "place of issue"),
    "permanent_address": ("noi thuong tru", "dia chi thuong tru", "thuong tru",
                          "dia chi", "address"),
    "position": ("chuc vu", "vi tri", "chuc danh", "position", "job title"),
    "unit": ("co so", "don vi", "truong", "unit", "chi nhanh"),
}


def _khong_dau(chuoi: str) -> str:
    bo = "".join(
        c for c in unicodedata.normalize("NFD", str(chuoi).lower())
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", bo).strip()


def _cau_hinh() -> tuple[dict, str, str | None]:
    khoa = os.environ.get("ECONTRACT_GOOGLE_KEY", "").strip()
    ma_sheet = os.environ.get("ECONTRACT_SHEET_ID", "").strip()
    if not khoa or not ma_sheet:
        raise ChuaCauHinh(
            "Chưa khai ECONTRACT_GOOGLE_KEY và ECONTRACT_SHEET_ID trên máy chủ."
        )
    try:
        thong_tin = json.loads(khoa)
    except json.JSONDecodeError as loi:
        raise ChuaCauHinh(
            "ECONTRACT_GOOGLE_KEY không phải JSON hợp lệ. Dán nguyên nội dung "
            "file khóa tải từ Google, kể cả hai dấu ngoặc nhọn."
        ) from loi
    if thong_tin.get("type") != "service_account":
        raise ChuaCauHinh(
            "Khóa này không phải khóa tài khoản máy. Tải lại loại "
            "service account key dạng JSON."
        )
    # Mã Sheet nằm giữa /d/ và /edit trong đường liên kết.
    khop = re.search(r"/d/([a-zA-Z0-9_-]{20,})", ma_sheet)
    if khop:
        ma_sheet = khop.group(1)
    return thong_tin, ma_sheet, os.environ.get("ECONTRACT_SHEET_TAB") or None


def da_cau_hinh() -> bool:
    try:
        _cau_hinh()
    except ChuaCauHinh:
        return False
    return True


def email_tai_khoan_may() -> str | None:
    """Email cần được chia sẻ Sheet; hiện ra để người dùng đối chiếu."""
    try:
        thong_tin, _, _ = _cau_hinh()
    except ChuaCauHinh:
        return None
    return thong_tin.get("client_email")


_khoa_ve = threading.Lock()
_ve: tuple[str, float] | None = None


def _lay_ve() -> str:
    """Đổi khóa JSON lấy vé vào cửa, giữ lại đến gần hết hạn."""
    global _ve
    with _khoa_ve:
        if _ve and _ve[1] > time.time() + 60:
            return _ve[0]
        thong_tin, _, _ = _cau_hinh()
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            giay_to = service_account.Credentials.from_service_account_info(
                thong_tin, scopes=[PHAM_VI]
            )
            giay_to.refresh(Request())
        except Exception as loi:
            raise LoiSheet(
                "Không dùng được khóa tài khoản máy. Kiểm tra lại nội dung "
                "khóa và xem đã bật Google Sheets API chưa."
            ) from loi
        han = giay_to.expiry.timestamp() if giay_to.expiry else time.time() + 300
        _ve = (giay_to.token, han)
        return _ve[0]


def _goi(duong_dan: str, tham_so: dict | None = None) -> dict:
    import httpx

    _, ma_sheet, _ = _cau_hinh()
    try:
        phan_hoi = httpx.get(
            f"{GOC_API}/{ma_sheet}{duong_dan}",
            headers={"Authorization": f"Bearer {_lay_ve()}"},
            params=tham_so or {},
            timeout=THOI_GIAN_CHO,
        )
    except httpx.HTTPError as loi:
        raise LoiSheet("Không kết nối được tới Google Sheets") from loi

    if phan_hoi.status_code == 403:
        raise LoiSheet(
            "Google từ chối truy cập. Hãy mở Sheet, bấm Chia sẻ và thêm email "
            f"{email_tai_khoan_may()} với quyền Editor."
        )
    if phan_hoi.status_code == 404:
        raise LoiSheet(
            "Không tìm thấy Sheet. Kiểm tra lại ECONTRACT_SHEET_ID."
        )
    if phan_hoi.status_code != 200:
        raise LoiSheet(f"Google Sheets trả lỗi {phan_hoi.status_code}")
    return phan_hoi.json()


def danh_sach_tab() -> list[str]:
    du_lieu = _goi("", {"fields": "sheets.properties.title"})
    return [t["properties"]["title"] for t in du_lieu.get("sheets", [])]


def _tab_dang_dung() -> str:
    _, _, tab = _cau_hinh()
    if tab:
        return tab
    cac_tab = danh_sach_tab()
    if not cac_tab:
        raise LoiSheet("Sheet này không có tab nào")
    return cac_tab[0]


def _doc_o() -> list[list[str]]:
    tab = _tab_dang_dung()
    du_lieu = _goi(f"/values/{tab}!A1:Z{SO_DONG_TOI_DA}",
                   {"majorDimension": "ROWS"})
    return du_lieu.get("values", [])


def doan_cot(tieu_de: list[str]) -> dict[str, int]:
    """Đoán cột nào ứng với trường nào, dựa vào tên cột ở dòng đầu."""
    ket_qua: dict[str, int] = {}
    da_dung: set[int] = set()
    # Xét tên dài trước để "ngày cấp" không bị "ngày" chung chung giành mất.
    ung_vien = sorted(
        ((truong, ten) for truong, ds in TEN_COT.items() for ten in ds),
        key=lambda x: -len(x[1]),
    )
    for truong, ten in ung_vien:
        if truong in ket_qua:
            continue
        for i, cot in enumerate(tieu_de):
            if i in da_dung:
                continue
            sach = _khong_dau(cot)
            if sach == ten or (len(ten) >= 6 and ten in sach):
                ket_qua[truong] = i
                da_dung.add(i)
                break
    return ket_qua


_khoa_nho = threading.Lock()
_nho: tuple[list[dict], dict[str, int], list[str], float] | None = None


def danh_sach_nhan_vien(lam_moi: bool = False) -> dict[str, Any]:
    """Đọc Sheet và trả về danh sách nhân viên đã quy về tên trường của form."""
    global _nho
    with _khoa_nho:
        if _nho and not lam_moi and time.time() - _nho[3] < THOI_GIAN_NHO:
            nhan_vien, cot, tieu_de, luc = _nho
            return {"employees": nhan_vien, "columns": cot,
                    "headers": tieu_de, "cached": True}

    o = _doc_o()
    if not o:
        raise LoiSheet("Tab đang dùng không có dữ liệu nào")

    tieu_de = [str(x) for x in o[0]]
    cot = doan_cot(tieu_de)
    if "full_name" not in cot:
        raise LoiSheet(
            "Không nhận ra cột họ tên. Đặt tên cột ở dòng đầu là "
            "\"Họ và tên\" rồi thử lại."
        )

    nhan_vien = []
    for dong in o[1:]:
        ban_ghi = {
            truong: str(dong[i]).strip() if i < len(dong) else ""
            for truong, i in cot.items()
        }
        if ban_ghi.get("full_name"):
            nhan_vien.append(ban_ghi)

    with _khoa_nho:
        _nho = (nhan_vien, cot, tieu_de, time.time())
    return {"employees": nhan_vien, "columns": cot,
            "headers": tieu_de, "cached": False}


def xoa_bo_nho() -> None:
    global _nho, _ve
    with _khoa_nho:
        _nho = None
    with _khoa_ve:
        _ve = None
