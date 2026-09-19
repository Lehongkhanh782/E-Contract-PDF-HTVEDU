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

# Bản scan căn cước thường một hoặc hai mặt; chặn tệp nhiều trang.
SO_TRANG_TOI_DA = 3
# 300 điểm/inch là mức Tesseract đọc tốt mà chưa tốn nhiều bộ nhớ.
DO_PHAN_GIAI = 300
# Bản scan đã được máy quét nhận chữ sẵn thì dùng luôn, khỏi đọc lại ảnh.
DU_CHU_DE_DUNG_LUON = 60

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
    """Tệp gửi lên không phải ảnh hoặc PDF đọc được."""


def la_pdf(du_lieu: bytes) -> bool:
    """Nhận diện PDF bằng dấu hiệu đầu tệp, không tin phần mở rộng."""
    return du_lieu[:5] == b"%PDF-"


def _poppler(ten: str) -> str:
    duong_dan = shutil.which(ten)
    if not duong_dan:
        raise OcrKhongSanSang(
            f"Máy chủ chưa cài {ten}. Cài gói poppler-utils để đọc được PDF."
        )
    return duong_dan


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
            f"Chỉ nhận ảnh JPG, PNG, WebP hoặc tệp PDF; "
            f"tệp này là {dinh_dang or 'không rõ'}"
        )
    if rong > KICH_THUOC_TOI_DA[0] or cao > KICH_THUOC_TOI_DA[1]:
        raise AnhKhongHopLe("Ảnh có kích thước quá lớn")


def _kiem_tra_pdf(du_lieu: bytes) -> int:
    """Xác nhận PDF đọc được và trả về số trang."""
    if len(du_lieu) > GIOI_HAN_BYTE:
        raise AnhKhongHopLe(
            f"Tệp lớn hơn {GIOI_HAN_BYTE // (1024 * 1024)} MB; "
            "quét lại với độ phân giải thấp hơn"
        )
    try:
        import io

        from pypdf import PdfReader

        so_trang = len(PdfReader(io.BytesIO(du_lieu)).pages)
    except Exception as loi:
        raise AnhKhongHopLe("Không mở được tệp này như một PDF") from loi
    if so_trang == 0:
        raise AnhKhongHopLe("PDF không có trang nào")
    if so_trang > SO_TRANG_TOI_DA:
        raise AnhKhongHopLe(
            f"PDF có {so_trang} trang; chỉ nhận tối đa {SO_TRANG_TOI_DA} trang. "
            "Tách riêng trang chứa giấy tờ rồi tải lại."
        )
    return so_trang


def _chu_co_san_trong_pdf(duong_dan: Path) -> str:
    """Lấy lớp chữ sẵn có, nếu máy quét đã nhận dạng chữ từ trước."""
    ket_qua = subprocess.run(
        [_poppler("pdftotext"), "-layout", str(duong_dan), "-"],
        capture_output=True, text=True, timeout=THOI_GIAN_TOI_DA,
    )
    return ket_qua.stdout if ket_qua.returncode == 0 else ""


def _doc_pdf(du_lieu: bytes) -> str:
    """Đọc PDF: ưu tiên lớp chữ sẵn có, không có thì dựng ảnh rồi nhận dạng."""
    _kiem_tra_pdf(du_lieu)
    tesseract = _tesseract()
    pdftoppm = _poppler("pdftoppm")

    with tempfile.TemporaryDirectory(prefix="econtract_pdf_") as thu_muc:
        goc = Path(thu_muc) / "nguon.pdf"
        goc.write_bytes(du_lieu)

        san_co = _chu_co_san_trong_pdf(goc)
        if len(san_co.strip()) >= DU_CHU_DE_DUNG_LUON:
            return san_co

        # Không có lớp chữ: dựng từng trang thành ảnh rồi nhận dạng.
        subprocess.run(
            [pdftoppm, "-r", str(DO_PHAN_GIAI), "-png",
             "-l", str(SO_TRANG_TOI_DA), str(goc), str(Path(thu_muc) / "trang")],
            capture_output=True, timeout=THOI_GIAN_TOI_DA * 2, check=True,
        )
        anh = sorted(Path(thu_muc).glob("trang*.png"))
        if not anh:
            raise RuntimeError("Không dựng được ảnh từ PDF này")

        phan = []
        for i, tep in enumerate(anh):
            ket_qua = subprocess.run(
                [tesseract, str(tep), str(Path(thu_muc) / f"ra{i}"), "-l", "vie"],
                capture_output=True, text=True, timeout=THOI_GIAN_TOI_DA,
            )
            ra = Path(thu_muc) / f"ra{i}.txt"
            if ket_qua.returncode == 0 and ra.is_file():
                phan.append(ra.read_text(encoding="utf-8", errors="replace"))
        if not phan:
            raise RuntimeError("Tesseract không đọc được trang nào trong PDF")
        return "\n".join(phan)


def doc_van_ban(du_lieu: bytes) -> str:
    """Đọc ảnh hoặc PDF và trả về văn bản thô."""
    if la_pdf(du_lieu):
        if not _cong_ocr.acquire(timeout=THOI_GIAN_TOI_DA):
            raise RuntimeError("Máy chủ đang bận đọc tệp khác. Chờ một lát rồi thử lại.")
        try:
            return _doc_pdf(du_lieu)
        finally:
            _cong_ocr.release()

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


# Ký tự máy quét hay thêm vào quanh nhãn, không phải nội dung thật.
NHIEU = r"[\s:.\-–—_|~·•]+"


def _bo_nhieu(doan: str) -> str:
    """Bỏ nhiễu hai đầu; còn lại dưới hai ký tự thì coi như không có gì."""
    sach = re.sub(rf"^{NHIEU}", "", doan)
    sach = re.sub(rf"{NHIEU}$", "", sach).strip()
    return sach if len(sach) >= 2 else ""


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
            # Máy quét hay thêm gạch hoặc chấm thừa sau nhãn, ví dụ
            # "Place of residence: -", nên phải bỏ nhiễu trước khi xét.
            ung_vien = _bo_nhieu(hien_tai[khop.end():])
            if not ung_vien:
                for tiep in dong[i + 1:]:
                    sach = _bo_nhieu(tiep)
                    if sach:
                        ung_vien = sach
                        break
            if ung_vien:
                ket_qua[ten] = CHUAN_HOA[ten](ung_vien)
            break

    return ket_qua


def doc_giay_to(du_lieu: bytes) -> dict:
    """Đọc ảnh hoặc PDF và trả về các trường gợi ý kèm cảnh báo bắt buộc."""
    van_ban = doc_van_ban(du_lieu)
    truong = tach_truong(van_ban)
    doc_duoc = [ten for ten, gia_tri in truong.items() if gia_tri]
    return {
        "fields": truong,
        "recognised": doc_duoc,
        "missing": [ten for ten in TRUONG if ten not in doc_duoc],
        "is_suggestion_only": True,
        "source_kind": "pdf" if la_pdf(du_lieu) else "image",
        "warning": (
            "Đây chỉ là gợi ý do máy đọc. Máy thường nhầm dấu tiếng Việt, "
            "nhất là ở họ tên. Đọc lại từng ô trước khi tạo hợp đồng."
        ),
        "raw_text": van_ban.strip(),
    }


def ho_tro_pdf() -> bool:
    """Máy chủ có công cụ đọc PDF không."""
    return all(shutil.which(t) for t in ("pdftoppm", "pdftotext"))


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
