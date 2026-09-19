"""Đọc ảnh giấy tờ tùy thân bằng Tesseract.

Kết quả chỉ là GỢI Ý để nhân sự sửa, không phải dữ liệu tin cậy. Tesseract
đọc sai dấu tiếng Việt cả trên ảnh sạch: trong đo thử nó đọc NGUYỄN thành
NGUYÊN. Vì vậy mọi trường đều phải được người kiểm tra lại trước khi dùng.

Không đoán: trường nào không đọc được hoặc không đúng dạng thì trả null.
Ảnh không được lưu lại; xử lý xong là xóa.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import threading
from datetime import date
from pathlib import Path

# Ảnh căn cước chụp bằng điện thoại thường dưới 5 MB.
GIOI_HAN_BYTE = 8 * 1024 * 1024
KICH_THUOC_TOI_DA = (6000, 6000)
THOI_GIAN_TOI_DA = 30

# Tesseract chỉ chiếm khoảng 39 MB nhưng vẫn giới hạn số lượt chạy cùng lúc
# để không cộng dồn với phần dựng PDF trên máy chủ 512 MB.
_cong_ocr = threading.BoundedSemaphore(2)

DINH_DANG_CHO_PHEP = {"JPEG", "PNG", "WEBP"}

# Nhãn trên thẻ căn cước. Mỗi nhãn kèm tên trường trong biểu mẫu.
NHAN = [
    ("identity_number", r"(?:số|so)\s*/?\s*(?:no\.?)?\s*:"),
    ("full_name", r"(?:họ và tên|ho va ten)\s*/?\s*(?:full name)?\s*:"),
    ("birth_date", r"(?:ngày sinh|ngay sinh)\s*/?\s*(?:date of birth)?\s*:"),
    ("gender", r"(?:giới tính|gioi tinh)\s*/?\s*(?:sex)?\s*:"),
    ("nationality", r"(?:quốc tịch|quoc tich)\s*/?\s*(?:nationality)?\s*:"),
    ("permanent_address",
     r"(?:nơi thường trú|noi thuong tru|nơi cư trú)\s*/?\s*(?:place of residence)?\s*:"),
]

TRUONG = [ten for ten, _ in NHAN]


class OcrKhongSanSang(RuntimeError):
    """Máy chủ chưa cài Tesseract hoặc gói tiếng Việt."""


class AnhKhongHopLe(ValueError):
    """Tệp gửi lên không phải ảnh đọc được."""


def _tesseract() -> str:
    duong_dan = shutil.which("tesseract")
    if not duong_dan:
        raise OcrKhongSanSang(
            "Máy chủ chưa cài Tesseract. Cài gói tesseract-ocr và "
            "tesseract-ocr-vie."
        )
    return duong_dan


def _kiem_tra_anh(du_lieu: bytes) -> None:
    """Xác nhận đây thật sự là ảnh, không chỉ tin phần mở rộng tệp."""
    if not du_lieu:
        raise AnhKhongHopLe("Tệp rỗng")
    if len(du_lieu) > GIOI_HAN_BYTE:
        raise AnhKhongHopLe(
            f"Ảnh lớn hơn {GIOI_HAN_BYTE // (1024 * 1024)} MB; "
            "chụp lại hoặc giảm kích thước"
        )
    try:
        import io

        from PIL import Image

        with Image.open(io.BytesIO(du_lieu)) as anh:
            anh.verify()
        with Image.open(io.BytesIO(du_lieu)) as anh:
            dinh_dang = (anh.format or "").upper()
            rong, cao = anh.size
    except AnhKhongHopLe:
        raise
    except Exception as loi:
        raise AnhKhongHopLe("Không đọc được tệp này như một ảnh") from loi

    if dinh_dang not in DINH_DANG_CHO_PHEP:
        raise AnhKhongHopLe(
            f"Chỉ nhận ảnh JPG, PNG hoặc WebP; tệp này là {dinh_dang or 'không rõ'}"
        )
    if rong > KICH_THUOC_TOI_DA[0] or cao > KICH_THUOC_TOI_DA[1]:
        raise AnhKhongHopLe("Ảnh có kích thước quá lớn")


def doc_van_ban(du_lieu: bytes) -> str:
    """Chạy Tesseract và trả về văn bản thô."""
    _kiem_tra_anh(du_lieu)
    lenh = _tesseract()

    if not _cong_ocr.acquire(timeout=THOI_GIAN_TOI_DA):
        raise RuntimeError("Máy chủ đang bận đọc ảnh khác. Chờ một lát rồi thử lại.")
    try:
        with tempfile.TemporaryDirectory(prefix="econtract_ocr_") as thu_muc:
            goc = Path(thu_muc) / "anh"
            goc.write_bytes(du_lieu)
            ket_qua = subprocess.run(
                [lenh, str(goc), str(Path(thu_muc) / "ra"), "-l", "vie"],
                capture_output=True,
                text=True,
                timeout=THOI_GIAN_TOI_DA,
            )
            ra = Path(thu_muc) / "ra.txt"
            if ket_qua.returncode != 0 or not ra.is_file():
                raise RuntimeError("Tesseract không đọc được ảnh này")
            return ra.read_text(encoding="utf-8", errors="replace")
    finally:
        _cong_ocr.release()


def _chuan_hoa_ngay(gia_tri: str) -> str | None:
    """dd/mm/yyyy trên thẻ -> yyyy-mm-dd cho biểu mẫu. Sai dạng thì trả None."""
    khop = re.search(r"\b(\d{1,2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{4})\b", gia_tri)
    if not khop:
        return None
    ngay, thang, nam = (int(p) for p in khop.groups())
    try:
        return date(nam, thang, ngay).isoformat()
    except ValueError:
        return None


def _chuan_hoa_so_giay_to(gia_tri: str) -> str | None:
    chi_so = re.sub(r"\D", "", gia_tri)
    return chi_so if 9 <= len(chi_so) <= 12 else None


def _chuan_hoa_gioi_tinh(gia_tri: str) -> str | None:
    thap = gia_tri.lower()
    if "nữ" in thap or "nu" in thap.split() or "female" in thap:
        return "Nữ"
    if "nam" in thap or "male" in thap:
        return "Nam"
    return None


def _chuan_hoa_ten(gia_tri: str) -> str | None:
    sach = re.sub(r"\s+", " ", gia_tri).strip(" .:,")
    # Tên chỉ gồm chữ và khoảng trắng; có số là đọc lẫn sang dòng khác.
    if not sach or re.search(r"\d", sach) or len(sach) < 3 or len(sach) > 100:
        return None
    return sach


def _chuan_hoa_chung(gia_tri: str) -> str | None:
    sach = re.sub(r"\s+", " ", gia_tri).strip(" .:,")
    return sach if 2 <= len(sach) <= 200 else None


CHUAN_HOA = {
    "identity_number": _chuan_hoa_so_giay_to,
    "full_name": _chuan_hoa_ten,
    "birth_date": _chuan_hoa_ngay,
    "gender": _chuan_hoa_gioi_tinh,
    "nationality": _chuan_hoa_chung,
    "permanent_address": _chuan_hoa_chung,
}


def tach_truong(van_ban: str) -> dict[str, str | None]:
    """Tách các trường từ văn bản thô. Không chắc thì trả None."""
    dong = [d.strip() for d in van_ban.splitlines()]
    ket_qua: dict[str, str | None] = {ten: None for ten in TRUONG}

    for i, hien_tai in enumerate(dong):
        if not hien_tai:
            continue
        for ten, mau in NHAN:
            if ket_qua[ten] is not None:
                continue
            khop = re.search(mau, hien_tai, re.IGNORECASE)
            if not khop:
                continue
            # Giá trị nằm ngay sau dấu hai chấm, hoặc ở dòng có chữ kế tiếp.
            phan_sau = hien_tai[khop.end():].strip()
            ung_vien = phan_sau
            if not ung_vien:
                for tiep in dong[i + 1:]:
                    if tiep:
                        ung_vien = tiep
                        break
            if ung_vien:
                ket_qua[ten] = CHUAN_HOA[ten](ung_vien)
            break

    return ket_qua


def doc_giay_to(du_lieu: bytes) -> dict:
    """Đọc ảnh và trả về các trường gợi ý kèm cảnh báo bắt buộc."""
    van_ban = doc_van_ban(du_lieu)
    truong = tach_truong(van_ban)
    doc_duoc = [ten for ten, gia_tri in truong.items() if gia_tri]
    return {
        "fields": truong,
        "recognised": doc_duoc,
        "missing": [ten for ten in TRUONG if ten not in doc_duoc],
        "is_suggestion_only": True,
        "warning": (
            "Đây chỉ là gợi ý do máy đọc. Máy thường nhầm dấu tiếng Việt, "
            "nhất là ở họ tên. Đọc lại từng ô trước khi tạo hợp đồng."
        ),
        "raw_text": van_ban.strip(),
    }


def san_sang() -> bool:
    """Máy chủ có Tesseract kèm gói tiếng Việt không."""
    if shutil.which("tesseract") is None:
        return False
    try:
        ket_qua = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return "vie" in ket_qua.stdout.split()
