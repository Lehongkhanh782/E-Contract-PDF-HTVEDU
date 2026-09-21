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
from datetime import datetime, timedelta, timezone
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
    "unit": ("co so", "don vi", "truong", "ma truong", "unit", "chi nhanh"),
    "status": ("trang thai", "tinh trang", "status"),
    # Trạng thái hợp đồng, tách riêng khỏi trạng thái làm việc: một người
    # đang làm bình thường vẫn có thể đang trong thời gian thử việc.
    # Tên dài hơn nên doan_cot xét trước, "trang thai" không giành mất cột
    # Trang_Thai_HD khi Sheet xếp cột đó đứng trước cột Trang_Thai.
    "contract_status": ("trang thai hd", "trang thai hop dong",
                        "tinh trang hd", "tinh trang hop dong",
                        "loai hop dong", "dien hop dong", "contract status"),
}

# Các trường chỉ dùng để lọc/đối chiếu, không đổ thẳng vào biểu mẫu.
TRUONG_PHU = ("status", "contract_status")


def _khong_dau(chuoi: str) -> str:
    """Bỏ dấu, viết thường, và coi gạch dưới/gạch ngang như khoảng trắng.

    Ứng dụng nhân sự đặt tên cột kiểu Ho_Ten, Ngay_Sinh; không quy về
    "ho ten", "ngay sinh" thì không cột nào khớp cả.
    """
    bo = "".join(
        c for c in unicodedata.normalize("NFD", str(chuoi).lower())
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[\s_\-]+", " ", bo).strip()


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


MO_DAU_PEM = "-----BEGIN PRIVATE KEY-----"
KET_PEM = "-----END PRIVATE KEY-----"


def soi_khoa(thong_tin: dict) -> dict[str, Any]:
    """Xem phần private_key có còn nguyên vẹn không, không lộ nội dung khóa.

    Ô nhập biến môi trường của Render hay nuốt mất dấu xuống dòng trong khối
    PEM, hoặc biến nó thành hai ký tự \\ và n. Khóa hỏng kiểu đó vẫn là JSON
    hợp lệ nên phải soi riêng mới thấy.
    """
    khoa = thong_tin.get("private_key")
    ma_khoa = str(thong_tin.get("private_key_id") or "")
    ket_qua: dict[str, Any] = {
        # Tám ký tự đầu đủ để đối chiếu xem có đúng khóa mình vừa tạo không,
        # mà không đủ để ai dùng được.
        "key_id_prefix": ma_khoa[:8] or None,
        "ok": False,
    }
    if not isinstance(khoa, str) or not khoa.strip():
        ket_qua["problem"] = "Khóa thiếu hẳn phần private_key."
        return ket_qua
    if MO_DAU_PEM not in khoa or KET_PEM not in khoa:
        ket_qua["problem"] = (
            "Phần private_key không còn dòng "
            f"{MO_DAU_PEM}. Dán lại nguyên nội dung file khóa."
        )
        return ket_qua
    if "\\n" in khoa and "\n" not in khoa:
        ket_qua["problem"] = (
            "Phần private_key đang là hai ký tự \\ và n thay vì dấu xuống "
            "dòng thật. Xóa biến ECONTRACT_GOOGLE_KEY rồi dán lại bằng cách "
            "mở file khóa, chọn hết, sao chép, dán vào ô giá trị."
        )
        return ket_qua
    than = khoa.split(MO_DAU_PEM, 1)[1].split(KET_PEM, 1)[0]
    if len(than.strip()) < 1000:
        ket_qua["problem"] = (
            "Phần private_key ngắn bất thường, nhiều khả năng bị cắt mất. "
            "Dán lại nguyên nội dung file khóa."
        )
        return ket_qua
    ket_qua["ok"] = True
    return ket_qua


def _giai_thich_loi_ve(loi: Exception) -> str:
    """Dịch lỗi của Google sang câu người dùng làm theo được."""
    chi_tiet = " ".join(str(x) for x in loi.args)
    thap = chi_tiet.lower()
    if "invalid_grant" in thap:
        return (
            "Google báo khóa không còn hiệu lực (invalid_grant). Thường là do "
            "khóa đã bị thu hồi hoặc tài khoản máy đã bị xóa. Hãy vào Google "
            "Cloud tạo khóa mới rồi dán lại vào ECONTRACT_GOOGLE_KEY."
        )
    if "invalid_client" in thap or "unauthorized_client" in thap:
        return (
            "Google không nhận ra tài khoản máy này (invalid_client). Kiểm tra "
            "lại xem tài khoản máy còn tồn tại trong dự án không."
        )
    if "service_disabled" in thap or "has not been used in project" in thap:
        return (
            "Dự án chưa bật Google Sheets API. Vào Google Cloud, tìm "
            "\"Google Sheets API\" rồi bấm Enable, đợi khoảng một phút."
        )
    if "requests library is not installed" in thap:
        return (
            "Máy chủ thiếu thư viện requests nên không xin được vé vào cửa. "
            "Đây là lỗi cài đặt của máy chủ, không phải do khóa hay Sheet: "
            "cần dựng lại máy chủ sau khi đã thêm requests vào requirements.txt."
        )
    if "could not deserialize" in thap or "no key" in thap or "asn1" in thap:
        return (
            "Nội dung khóa bị hỏng nên không đọc được. Xóa biến "
            "ECONTRACT_GOOGLE_KEY rồi dán lại nguyên văn file khóa."
        )
    if "timed out" in thap or "connection" in thap or "resolve" in thap:
        return "Máy chủ không kết nối được tới Google để xin vé vào cửa."
    return (
        "Không dùng được khóa tài khoản máy. Google trả về: "
        + chi_tiet[:300]
    )


_khoa_ve = threading.Lock()
_ve: tuple[str, float] | None = None


def _lay_ve() -> str:
    """Đổi khóa JSON lấy vé vào cửa, giữ lại đến gần hết hạn."""
    global _ve
    with _khoa_ve:
        if _ve and _ve[1] > time.time() + 60:
            return _ve[0]
        thong_tin, _, _ = _cau_hinh()
        soi = soi_khoa(thong_tin)
        if not soi["ok"]:
            raise LoiSheet(soi["problem"])
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            giay_to = service_account.Credentials.from_service_account_info(
                thong_tin, scopes=[PHAM_VI]
            )
            giay_to.refresh(Request())
        except Exception as loi:
            raise LoiSheet(_giai_thich_loi_ve(loi)) from loi
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
    return _doc_phan_hoi(phan_hoi)


def _ghi(duong_dan: str, than: dict, tham_so: dict | None = None) -> dict:
    """Gửi dữ liệu lên Sheet. Cần tài khoản máy có quyền Editor."""
    import httpx

    _, ma_sheet, _ = _cau_hinh()
    try:
        phan_hoi = httpx.post(
            f"{GOC_API}/{ma_sheet}{duong_dan}",
            headers={"Authorization": f"Bearer {_lay_ve()}"},
            params=tham_so or {},
            json=than,
            timeout=THOI_GIAN_CHO,
        )
    except httpx.HTTPError as loi:
        raise LoiSheet("Không kết nối được tới Google Sheets") from loi
    return _doc_phan_hoi(phan_hoi, ghi=True)


def _doc_phan_hoi(phan_hoi, ghi: bool = False) -> dict:
    if phan_hoi.status_code == 403:
        # Cùng mã 403 nhưng hai nguyên nhân khác hẳn nhau: chưa bật API, hay
        # chưa chia sẻ Sheet. Đọc nội dung trả về mới phân biệt được.
        if "SERVICE_DISABLED" in phan_hoi.text or "has not been used" in phan_hoi.text:
            raise LoiSheet(
                "Dự án chưa bật Google Sheets API. Vào Google Cloud, tìm "
                "\"Google Sheets API\" rồi bấm Enable, đợi khoảng một phút "
                "rồi tải lại trang này."
            )
        raise LoiSheet(
            "Google từ chối "
            + ("ghi vào" if ghi else "truy cập")
            + ". Hãy mở Sheet, bấm Chia sẻ và thêm email "
            f"{email_tai_khoan_may()} với quyền Editor "
            "(quyền Viewer chỉ đọc được, không ghi được)."
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


# Tên tab chứa danh sách nhân viên, viết không dấu và viết thường. Sheet
# dùng chung với ứng dụng nhân sự có cả chục tab, tab đầu tiên thường là
# hướng dẫn chứ không phải dữ liệu, nên phải tìm theo tên.
TEN_TAB_NHAN_SU = (
    "nhan su", "nhan vien", "danh sach nhan su", "danh sach nhan vien",
    "ho so nhan su", "employees", "employee", "staff", "personnel",
)


def chon_tab(cac_tab: list[str]) -> str:
    """Chọn tab nhiều khả năng chứa danh sách nhân viên nhất."""
    if not cac_tab:
        raise LoiSheet("Sheet này không có tab nào")
    sach = {ten: _khong_dau(ten) for ten in cac_tab}
    # Trùng khít tên trước, rồi mới tới tên có chứa từ khóa, để "NHAN_SU"
    # được chọn thay vì "LICH_SU_NHAN_SU" nếu Sheet có cả hai.
    for ten_mau in TEN_TAB_NHAN_SU:
        for ten, gon in sach.items():
            if gon == ten_mau:
                return ten
    for ten_mau in TEN_TAB_NHAN_SU:
        for ten, gon in sach.items():
            if ten_mau in gon:
                return ten
    return cac_tab[0]


def _tab_dang_dung() -> str:
    _, _, tab = _cau_hinh()
    if tab:
        return tab
    return chon_tab(danh_sach_tab())


def _doc_o() -> tuple[str, list[list[str]]]:
    tab = _tab_dang_dung()
    du_lieu = _goi(f"/values/{tab}!A1:Z{SO_DONG_TOI_DA}",
                   {"majorDimension": "ROWS"})
    return tab, du_lieu.get("values", [])


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
_nho: tuple[list[dict], dict[str, int], list[str], str, float] | None = None


def danh_sach_nhan_vien(lam_moi: bool = False) -> dict[str, Any]:
    """Đọc Sheet và trả về danh sách nhân viên đã quy về tên trường của form."""
    global _nho
    with _khoa_nho:
        if _nho and not lam_moi and time.time() - _nho[4] < THOI_GIAN_NHO:
            nhan_vien, cot, tieu_de, tab, luc = _nho
            return {"employees": nhan_vien, "columns": cot,
                    "headers": tieu_de, "tab": tab, "cached": True}

    tab, o = _doc_o()
    if not o:
        raise LoiSheet(f"Tab \"{tab}\" không có dữ liệu nào")

    tieu_de = [str(x) for x in o[0]]
    cot = doan_cot(tieu_de)
    if "full_name" not in cot:
        # Nói rõ đang đọc tab nào và thấy những cột gì, để biết là chọn nhầm
        # tab hay là tên cột khác với dự kiến.
        thay = ", ".join(t for t in tieu_de if t.strip()) or "(không có cột nào)"
        raise LoiSheet(
            f"Đang đọc tab \"{tab}\" nhưng không nhận ra cột họ tên. "
            f"Các cột thấy được ở dòng đầu: {thay}. "
            "Nếu đây không phải tab chứa danh sách nhân viên, hãy khai "
            "ECONTRACT_SHEET_TAB trên máy chủ bằng đúng tên tab cần đọc."
        )

    nhan_vien = []
    for dong in o[1:]:
        ban_ghi = {
            truong: str(dong[i]).strip() if i < len(dong) else ""
            for truong, i in cot.items()
        }
        if not ban_ghi.get("full_name"):
            continue
        if not con_lam_viec(ban_ghi.get("status")):
            continue
        # Quy mã cơ sở và chức vụ về đúng tên trong cấu hình hợp đồng; không
        # khớp thì để trống cho người dùng tự chọn.
        ban_ghi["unit_id"] = doi_ma_don_vi(ban_ghi.get("unit"))
        ban_ghi["position_id"] = doi_chuc_vu(ban_ghi.get("position"))
        # Để màn hình hợp đồng thử việc chỉ hiện đúng người đang thử việc.
        ban_ghi["employment_type"] = (
            "probation"
            if dang_thu_viec(ban_ghi.get("contract_status"),
                             ban_ghi.get("status"))
            else "official"
        )
        nhan_vien.append(ban_ghi)

    with _khoa_nho:
        _nho = (nhan_vien, cot, tieu_de, tab, time.time())
    return {"employees": nhan_vien, "columns": cot,
            "headers": tieu_de, "tab": tab, "cached": False}


# Trạng thái cho biết người đó đã nghỉ. So khớp không dấu, viết thường.
TRANG_THAI_DA_NGHI = ("nghi viec", "da nghi", "thoi viec", "nghi", "ngung",
                      "inactive", "resigned", "terminated")

# Trạng thái cho biết người đó đang trong thời gian thử việc.
TRANG_THAI_THU_VIEC = ("thu viec", "probation", "probationary")
# Nhưng "đã thử việc xong" thì ngược lại: người đó đã qua thử việc rồi.
# Không xét mấy chữ này thì danh sách thử việc sẽ lẫn cả người đã ký chính thức.
DAU_HIEU_HET_THU_VIEC = ("xong", "het", "ket thuc", "da qua", "hoan thanh",
                         "chinh thuc", "completed", "passed")


def dang_thu_viec(*trang_thai: str | None) -> bool:
    """Có ô nào đánh dấu người này đang thử việc không.

    Nhận nhiều ô vì dấu hiệu nằm ở cột Trang_Thai_HD, nhưng có nơi ghi
    thẳng vào cột Trang_Thai. Xét lần lượt, ô đầu tiên nói được điều gì
    thì lấy điều đó; ô trống thì hỏi tiếp ô sau.

    Tất cả đều trống, hoặc ghi chữ không nhận ra, thì coi là KHÔNG thử
    việc. Ngược hẳn với con_lam_viec: ở đó không rõ thì giữ lại cho khỏi
    mất người, còn ở đây không rõ mà đoán là thử việc thì sẽ in nhầm loại
    hợp đồng.
    """
    for o in trang_thai:
        if not o or not o.strip():
            continue
        # Ô đầu tiên có chữ là ô quyết định. Ghi CHINH_THUC ở cột hợp đồng
        # thì dừng luôn tại đó, không được rơi xuống hỏi cột Trang_Thai rồi
        # lật ngược kết luận.
        gon = _khong_dau(o)
        if not any(dau in gon for dau in TRANG_THAI_THU_VIEC):
            return False
        return not any(dau in gon for dau in DAU_HIEU_HET_THU_VIEC)
    return False


def con_lam_viec(trang_thai: str | None) -> bool:
    """Bỏ trống hoặc không nhận ra thì coi như còn làm, để không mất người."""
    if not trang_thai:
        return True
    gon = _khong_dau(trang_thai)
    return not any(dau in gon for dau in TRANG_THAI_DA_NGHI)


def doi_ma_don_vi(gia_tri: str | None) -> str | None:
    """Đổi mã cơ sở trên Sheet thành unit_id trong cấu hình hợp đồng."""
    if not gia_tri:
        return None
    from app import config

    gon = _khong_dau(gia_tri)
    for don_vi in config.units():
        ung_vien = [don_vi.get("code"), don_vi.get("display_name"),
                    don_vi.get("workplace_institution_name")]
        ung_vien += don_vi.get("hr_sheet_codes") or []
        if any(x and _khong_dau(x) == gon for x in ung_vien):
            return don_vi["unit_id"]
    return None


def doi_chuc_vu(gia_tri: str | None) -> str | None:
    """Đổi chức vụ trên Sheet thành position_id trong cấu hình hợp đồng.

    Không khớp thì trả None để người dùng tự chọn, chứ không gán bừa một vị
    trí — mỗi vị trí kéo theo mức lương cơ sở và việc có phải ký thỏa thuận
    trách nhiệm hay không.
    """
    if not gia_tri:
        return None
    from app import config

    gon = _khong_dau(gia_tri)
    for vi_tri in config.positions():
        ung_vien = [vi_tri.get("title"), vi_tri.get("role_label")]
        ung_vien += vi_tri.get("hr_sheet_titles") or []
        if any(x and _khong_dau(x) == gon for x in ung_vien):
            return vi_tri["position_id"]
    return None


def hieu_truong_tung_co_so() -> dict[str, str]:
    """Tên hiệu trưởng của từng cơ sở, đọc từ chính Sheet nhân sự.

    Lấy từ Sheet chứ không chép vào cấu hình, để đổi hiệu trưởng thì chỉ
    sửa một nơi. Cơ sở có nhiều người ghi chức vụ hiệu trưởng thì bỏ qua,
    không tự chọn hộ ai.
    """
    nhan_vien = danh_sach_nhan_vien()["employees"]
    theo_co_so: dict[str, list[str]] = {}
    for nv in nhan_vien:
        if nv.get("position_id") != "principal":
            continue
        ma = nv.get("unit_id")
        ten = (nv.get("full_name") or "").strip()
        if ma and ten:
            theo_co_so.setdefault(ma, []).append(ten)
    return {ma: ds[0] for ma, ds in theo_co_so.items() if len(ds) == 1}


# ---------------------------------------------------------------------------
# Lịch sử hợp đồng
#
# Mỗi lần tạo PDF thành công, ghi một dòng vào tab riêng trong cùng Sheet.
# Nhờ vậy lần sau chọn lại người đó thì biết ngay là đã cấp hợp đồng rồi,
# và kế toán có chỗ đối chiếu số hợp đồng đã phát hành.
#
# Ghi vào chính Sheet nhân sự chứ không dựng cơ sở dữ liệu riêng: máy chủ
# Render bản miễn phí xóa sạch đĩa mỗi lần dựng lại, nên dữ liệu để trong
# máy chủ là mất. Sheet thì nhà trường vẫn mở xem và sửa được bằng tay.
# ---------------------------------------------------------------------------

TAB_LICH_SU = "LICH_SU_HOP_DONG"
COT_LICH_SU = ("Thoi_Diem", "Ma_Nhan_Vien", "Ho_Ten", "Ma_Truong",
               "Loai_Hop_Dong", "So_Hop_Dong", "Ngay_Ky", "Nguoi_Tao")
# Giờ Việt Nam. Không dùng giờ của máy chủ vì Render chạy theo giờ UTC,
# ghi vào Sheet sẽ lệch 7 tiếng và người đọc tưởng là hợp đồng làm lúc nửa đêm.
MUI_GIO_VN = timezone(timedelta(hours=7))
TEN_LOAI_HOP_DONG = {
    "official": "Hợp đồng lao động",
    "probation": "Hợp đồng thử việc",
}


def _bay_gio() -> str:
    return datetime.now(MUI_GIO_VN).strftime("%d/%m/%Y %H:%M")


def _tao_tab_lich_su() -> None:
    """Tạo tab lịch sử kèm dòng tiêu đề, nếu Sheet chưa có tab đó."""
    _ghi(":batchUpdate", {
        "requests": [{"addSheet": {"properties": {"title": TAB_LICH_SU}}}]
    })
    _ghi(
        f"/values/{TAB_LICH_SU}!A1:append",
        {"values": [list(COT_LICH_SU)]},
        {"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
    )


def ghi_lich_su(ban_ghi: dict) -> None:
    """Thêm một dòng vào tab lịch sử. Tab chưa có thì tự tạo.

    Người gọi phải tự bắt lỗi: không ghi được lịch sử là chuyện đáng báo,
    nhưng không được vì thế mà hủy mất cái PDF đã dựng xong.
    """
    if TAB_LICH_SU not in danh_sach_tab():
        _tao_tab_lich_su()
    dong = [
        _bay_gio(),
        str(ban_ghi.get("code") or ""),
        str(ban_ghi.get("full_name") or ""),
        str(ban_ghi.get("unit_id") or ""),
        TEN_LOAI_HOP_DONG.get(str(ban_ghi.get("contract_type")),
                              str(ban_ghi.get("contract_type") or "")),
        str(ban_ghi.get("contract_number") or ""),
        str(ban_ghi.get("signing_date") or ""),
        str(ban_ghi.get("created_by") or ""),
    ]
    _ghi(
        f"/values/{TAB_LICH_SU}!A1:append",
        {"values": [dong]},
        # RAW để Google khỏi tự hiểu "12/09/2026" thành ngày rồi đổi cách
        # hiển thị, và khỏi coi mã nhân viên toàn số là con số.
        {"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
    )
    xoa_nho_lich_su()


_khoa_lich_su = threading.Lock()
_nho_lich_su: tuple[dict[str, list[dict]], float] | None = None


def lich_su_theo_ma(lam_moi: bool = False) -> dict[str, list[dict]]:
    """Lịch sử đã ghi, gom theo mã nhân viên, mới nhất đứng trước.

    Chưa có tab lịch sử nghĩa là chưa cấp hợp đồng nào — trả rỗng, không
    phải lỗi.
    """
    global _nho_lich_su
    with _khoa_lich_su:
        if (_nho_lich_su and not lam_moi
                and time.time() - _nho_lich_su[1] < THOI_GIAN_NHO):
            return _nho_lich_su[0]

    if TAB_LICH_SU not in danh_sach_tab():
        ket_qua: dict[str, list[dict]] = {}
    else:
        du_lieu = _goi(f"/values/{TAB_LICH_SU}!A1:H{SO_DONG_TOI_DA}",
                       {"majorDimension": "ROWS"})
        ket_qua = _gom_lich_su(du_lieu.get("values", []))

    with _khoa_lich_su:
        _nho_lich_su = (ket_qua, time.time())
    return ket_qua


def _gom_lich_su(o: list[list[str]]) -> dict[str, list[dict]]:
    """Đổi các ô đọc được thành lịch sử gom theo mã nhân viên."""
    theo_ma: dict[str, list[dict]] = {}
    for dong in o[1:]:
        gia_tri = [str(dong[i]).strip() if i < len(dong) else ""
                   for i in range(len(COT_LICH_SU))]
        ban_ghi = dict(zip(
            ("created_at", "code", "full_name", "unit_id", "contract_type",
             "contract_number", "signing_date", "created_by"),
            gia_tri,
        ))
        # Không có mã nhân viên thì không tra lại được, nhưng vẫn là dòng
        # có thật trong Sheet nên giữ dưới khóa rỗng thay vì bỏ đi.
        if not ban_ghi["full_name"] and not ban_ghi["code"]:
            continue
        theo_ma.setdefault(ban_ghi["code"], []).insert(0, ban_ghi)
    return theo_ma


def xoa_nho_lich_su() -> None:
    global _nho_lich_su
    with _khoa_lich_su:
        _nho_lich_su = None


def gia_tri_khac_nhau(nhan_vien: list[dict], truong: str,
                      toi_da: int = 40) -> list[str] | None:
    """Liệt kê các giá trị khác nhau của một cột, để đối chiếu với cấu hình.

    Chỉ dùng cho cột phân loại như cơ sở, chức vụ, trạng thái — tuyệt đối
    không dùng cho cột chứa thông tin cá nhân như họ tên hay số giấy tờ.
    """
    if truong not in TEN_COT or truong in ("full_name", "identity_number",
                                           "birth_date", "permanent_address",
                                           "code"):
        return None
    thay: list[str] = []
    for nv in nhan_vien:
        gia_tri = (nv.get(truong) or "").strip()
        if gia_tri and gia_tri not in thay:
            thay.append(gia_tri)
            if len(thay) >= toi_da:
                break
    return sorted(thay)


def xoa_bo_nho() -> None:
    global _nho, _ve
    xoa_nho_lich_su()
    with _khoa_nho:
        _nho = None
    with _khoa_ve:
        _ve = None


def chan_doan() -> dict[str, Any]:
    """Thông tin để dò lỗi cấu hình, tuyệt đối không kèm nội dung khóa."""
    try:
        thong_tin, ma_sheet, tab = _cau_hinh()
    except ChuaCauHinh as loi:
        return {"configured": False, "note": str(loi)}
    soi = soi_khoa(thong_tin)
    return {
        "configured": True,
        "service_account": thong_tin.get("client_email"),
        "project": thong_tin.get("project_id"),
        "sheet_id": ma_sheet,
        "sheet_tab": tab,
        "key_id_prefix": soi["key_id_prefix"],
        "key_looks_valid": soi["ok"],
        **({"key_problem": soi["problem"]} if not soi["ok"] else {}),
    }
