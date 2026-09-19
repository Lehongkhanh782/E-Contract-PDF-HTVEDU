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
import unicodedata
from datetime import date
from pathlib import Path

# Ảnh căn cước chụp bằng điện thoại thường dưới 5 MB.
GIOI_HAN_BYTE = 8 * 1024 * 1024
KICH_THUOC_TOI_DA = (6000, 6000)
# Ảnh điện thoại thường 3000 đến 4000 điểm. Thu về mức này vẫn đọc tốt mà
# nhanh hơn nhiều trên máy chủ yếu.
CANH_DAI_TOI_DA = 2400
THOI_GIAN_TOI_DA = 45

# Tesseract chỉ chiếm khoảng 39 MB nhưng vẫn giới hạn số lượt chạy cùng lúc
# để không cộng dồn với phần dựng PDF trên máy chủ 512 MB.
_cong_ocr = threading.BoundedSemaphore(2)

DINH_DANG_CHO_PHEP = {"JPEG", "PNG", "WEBP"}

# Bản scan căn cước thường một hoặc hai mặt; chặn tệp nhiều trang.
SO_TRANG_TOI_DA = 3
# Mặt trước, mặt sau và một bản dự phòng là đủ cho mọi trường hợp thực tế.
SO_TEP_TOI_DA = 3
# 200 điểm/inch đủ để đọc thẻ trên trang A4 mà dựng ảnh nhanh gấp đôi so
# với 300. Ở 300, riêng bước dựng ảnh một PDF hai trang đã mất gần 16 giây
# và làm cả yêu cầu vượt quá thời gian cho phép.
DO_PHAN_GIAI = 200
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


def _chay(lenh: list[str], giay: int | None = None) -> subprocess.CompletedProcess:
    """Gọi lệnh ngoài và đổi mọi sự cố thành thông báo hiểu được.

    Thiếu chỗ này thì quá thời gian sẽ ném subprocess.TimeoutExpired, không
    lớp nào bắt, và người dùng nhận lỗi 500 không biết vì sao.
    """
    try:
        return subprocess.run(
            lenh, capture_output=True, text=True,
            timeout=giay or THOI_GIAN_TOI_DA,
        )
    except subprocess.TimeoutExpired as loi:
        raise RuntimeError(
            "Đọc tệp quá lâu nên đã dừng. Tệp có thể quá lớn hoặc quá nhiều "
            "chi tiết. Thử chụp thẳng thẻ bằng điện thoại thay vì tải bản "
            "quét nhiều trang."
        ) from loi
    except (OSError, subprocess.SubprocessError) as loi:
        raise RuntimeError("Máy chủ không chạy được công cụ đọc tệp") from loi


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
    ket_qua = _chay([_poppler("pdftotext"), "-layout", str(duong_dan), "-"])
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
        _chay(
            [pdftoppm, "-r", str(DO_PHAN_GIAI), "-png",
             "-l", str(SO_TRANG_TOI_DA), str(goc), str(Path(thu_muc) / "trang")],
            giay=THOI_GIAN_TOI_DA,
        )
        anh = sorted(Path(thu_muc).glob("trang*.png"))
        if not anh:
            raise RuntimeError("Không dựng được ảnh từ PDF này")

        phan = []
        for i, tep in enumerate(anh):
            rieng = Path(thu_muc) / f"trang{i}"
            rieng.mkdir(exist_ok=True)
            try:
                phan.append(_doc_nhieu_luot(tesseract, tep, rieng, CHE_DO_PDF))
            except RuntimeError:
                continue
        if not phan:
            raise RuntimeError("Tesseract không đọc được trang nào trong PDF")
        return "\n".join(phan)


def _thu_nho_neu_can(du_lieu: bytes) -> bytes:
    """Thu ảnh quá lớn về kích thước vừa đủ để đọc, cho nhanh."""
    import io

    from PIL import Image

    with Image.open(io.BytesIO(du_lieu)) as anh:
        if max(anh.size) <= CANH_DAI_TOI_DA:
            return du_lieu
        ty_le = CANH_DAI_TOI_DA / max(anh.size)
        nho = anh.convert("RGB").resize(
            (round(anh.width * ty_le), round(anh.height * ty_le)),
            Image.LANCZOS,
        )
        bo_nho = io.BytesIO()
        nho.save(bo_nho, format="PNG")
        return bo_nho.getvalue()


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
            goc = Path(thu_muc) / "anh.png"
            goc.write_bytes(_thu_nho_neu_can(du_lieu))
            return _doc_nhieu_luot(lenh, goc, Path(thu_muc))
    finally:
        _cong_ocr.release()


# Ba chế độ bổ sung cho nhau: chế độ 3 đọc tốt các dòng liền mạch như số
# và họ tên; chế độ 11 đọc chữ nằm rời rạc; chế độ 6 coi cả ảnh là một khối
# nên bắt được dòng địa chỉ mà hai chế độ kia bỏ sót trên ảnh chụp nghiêng.
# Gộp kết quả cả ba rồi mới tách trường.
CHE_DO = (3, 11, 6)
# Ảnh dựng từ PDF rất lớn nên chỉ chạy hai chế độ, tránh quá thời gian.
CHE_DO_PDF = (3, 11)


# Chỉ dừng sớm khi địa chỉ đạt mức điểm này. Đủ sáu trường thôi chưa đủ:
# lượt đọc đầu có thể trả về một mảnh rác vẫn qua được bộ lọc, trong khi
# lượt sau mới lấy đúng dòng địa chỉ. Đo trên dữ liệu thật: mảnh rác và
# địa chỉ mờ đều quanh 11 điểm, địa chỉ đọc rõ đạt gần 30.
DIEM_DIA_CHI_DU_TOT = 16


def _du_tot_de_dung(van_ban: str) -> bool:
    truong = tach_truong(van_ban)
    if not all(truong.values()):
        return False
    return _diem_dia_chi(truong["permanent_address"] or "") >= DIEM_DIA_CHI_DU_TOT


def _doc_nhieu_luot(tesseract: str, anh: Path, thu_muc: Path,
                    che_do_list: tuple[int, ...] = CHE_DO) -> str:
    """Đọc lần lượt từng chế độ, đủ trường thì dừng.

    Máy chủ gói miễn phí chỉ có một phần mười nhân xử lý nên mỗi lượt đọc
    chậm hơn máy phát triển hàng chục lần. Chạy đủ ba lượt mọi lúc là lý do
    người dùng gặp lỗi quá thời gian. Lượt nào quá giờ thì bỏ qua lượt đó
    chứ không làm hỏng cả yêu cầu.
    """
    phan: list[str] = []
    for che_do in che_do_list:
        ra = thu_muc / f"ra{che_do}"
        try:
            ket_qua = _chay(
                [tesseract, str(anh), str(ra), "-l", "vie", "--psm", str(che_do)]
            )
        except RuntimeError:
            continue
        tep = ra.with_suffix(".txt")
        if ket_qua.returncode == 0 and tep.is_file():
            phan.append(tep.read_text(encoding="utf-8", errors="replace"))
            gop = "\n".join(phan)
            if _du_tot_de_dung(gop):
                return gop
    if not phan:
        raise RuntimeError(
            "Máy chủ không đọc được tệp này trong thời gian cho phép. "
            "Thử chụp thẳng thẻ bằng điện thoại, ảnh nhỏ gọn hơn."
        )
    return "\n".join(phan)


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


# Máy quét đọc nhãn rất hay sai: "Số / No.:" thành "SIING;", "Date of
# birth:" thành "Date of bifh:". Vì vậy không bám vào nhãn mà nhận dạng
# theo hình dạng của chính dữ liệu, rồi chỉ dùng nhãn để chọn khi có nhiều
# ứng viên.

NHIEU = r"[\s:.\-–—_|~·•!/]+"

# Dòng tiêu đề in hoa trên thẻ, không phải họ tên.
KHONG_PHAI_TEN = (
    "CỘNG HÒA", "XÃ HỘI", "CHỦ NGHĨA", "ĐỘC LẬP", "TỰ DO", "HẠNH PHÚC",
    "SOCIALIST", "REPUBLIC", "INDEPENDENCE", "FREEDOM", "HAPPINESS",
    "CĂN CƯỚC", "CÔNG DÂN", "CITIZEN", "IDENTITY", "CARD", "VIET NAM",
    "VIỆT NAM", "CHỨNG MINH", "CỤC TRƯỞNG", "CẢNH SÁT", "CÔNG AN",
    "DIRECTOR", "POLICE", "DEPARTMENT", "FULL NAME", "PLACE",
    # Mặt sau thẻ và dấu chứng thực của phường, không phải họ tên.
    "HĐND", "UBND", "UBNP", "HÀNH CHÍNH", "TRẬT TỰ", "QUẢN LÝ",
    "CHỨNG THỰC", "QUYỂN SỐ", "CHỦ TỊCH", "VĂN PHÒNG", "CÔNG CHỨC",
    "NGÓN TRỎ", "ĐẶC ĐIỂM", "NHẬN DẠNG", "BẢN SAO", "BẢN CHÍNH",
    "GENERAL", "ADMINISTRATIVE", "MANAGEMENT", "SOCIAL", "ORDER",
    "INDEX", "FINGER", "PERSONAL",
)

# Tuổi hợp lý của người lao động, dùng để loại ngày cấp và ngày hết hạn.
TUOI_NHO_NHAT = 14
TUOI_LON_NHAT = 80

MAU_NGAY = re.compile(r"\b(\d{1,2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{4})\b")
# Căn cước 12 số, chứng minh cũ 9 số. Cho phép khoảng trắng chen giữa.
MAU_SO_12 = re.compile(r"(?<!\d)(\d[\s.]{0,2}){11}\d(?!\d)")
MAU_SO_9 = re.compile(r"(?<!\d)(\d[\s.]{0,2}){8}\d(?!\d)")


def _bo_nhieu(doan: str) -> str:
    """Bỏ nhiễu hai đầu; còn lại dưới hai ký tự thì coi như không có gì."""
    sach = re.sub(rf"^{NHIEU}", "", doan)
    sach = re.sub(rf"{NHIEU}$", "", sach).strip()
    return sach if len(sach) >= 2 else ""


def _khong_dau(chuoi: str) -> str:
    """Bỏ dấu tiếng Việt để so khớp nhãn bất kể máy đọc sai dấu."""
    return "".join(
        c for c in unicodedata.normalize("NFD", chuoi.lower())
        if unicodedata.category(c) != "Mn"
    )


def _tim_so_giay_to(van_ban: str) -> str | None:
    """Căn cước là dãy 12 số; không có thì thử chứng minh 9 số."""
    for mau in (MAU_SO_12, MAU_SO_9):
        for khop in mau.finditer(van_ban):
            chi_so = re.sub(r"\D", "", khop.group(0))
            if len(chi_so) in (9, 12):
                return chi_so
    return None


def _tim_ten(dong: list[str]) -> str | None:
    """Họ tên là dòng in hoa toàn bộ, nhiều chữ, không lẫn chữ số.

    Ưu tiên dòng nằm ngay sau nhãn họ tên nếu nhận ra được nhãn đó.
    """
    def hop_le(d: str) -> bool:
        sach = _bo_nhieu(d)
        if not (5 <= len(sach) <= 60):
            return False
        if re.search(r"\d", sach):
            return False
        if not re.fullmatch(r"[^\W\d_]+(?:\s+[^\W\d_]+){1,5}", sach):
            return False
        if sach != sach.upper():
            return False
        thuong = _khong_dau(sach)
        return not any(_khong_dau(x) in thuong for x in KHONG_PHAI_TEN)

    for i, d in enumerate(dong):
        if "ho va ten" in _khong_dau(d) or "full name" in _khong_dau(d):
            phan_sau = _bo_nhieu(re.split(r"(?i)full\s*name", d)[-1])
            if hop_le(phan_sau):
                return re.sub(r"\s+", " ", _bo_nhieu(phan_sau))
            for tiep in dong[i + 1:]:
                if _bo_nhieu(tiep) and hop_le(tiep):
                    return re.sub(r"\s+", " ", _bo_nhieu(tiep))
                if _bo_nhieu(tiep):
                    break
    ung_vien = [d for d in dong if hop_le(d)]
    return re.sub(r"\s+", " ", _bo_nhieu(ung_vien[0])) if ung_vien else None


def _tim_ngay_sinh(dong: list[str]) -> str | None:
    """Trong các ngày đọc được, chọn ngày hợp lý với tuổi người lao động."""
    hom_nay = date.today()

    def hop_le(ngay: date) -> bool:
        tuoi = (hom_nay - ngay).days / 365.25
        return TUOI_NHO_NHAT <= tuoi <= TUOI_LON_NHAT

    uu_tien: list[date] = []
    con_lai: list[date] = []
    for d in dong:
        gan_nhan = "sinh" in _khong_dau(d) or "birth" in _khong_dau(d)
        for khop in MAU_NGAY.finditer(d):
            ngay, thang, nam = (int(x) for x in khop.groups())
            try:
                gia_tri = date(nam, thang, ngay)
            except ValueError:
                continue
            if not hop_le(gia_tri):
                continue
            (uu_tien if gan_nhan else con_lai).append(gia_tri)
    chon = uu_tien or con_lai
    return chon[0].isoformat() if chon else None


def _tim_gioi_tinh(dong: list[str]) -> str | None:
    """Giá trị có thể nằm cùng dòng nhãn hoặc ở dòng kế tiếp."""

    def doc(doan: str) -> str | None:
        thuong = _khong_dau(doan)
        if "Nữ" in doan or re.search(r"\bnu\b", thuong):
            return "Nữ"
        if re.search(r"\bnam\b", thuong):
            return "Nam"
        return None

    for i, d in enumerate(dong):
        thuong = _khong_dau(d)
        if "gioi tinh" not in thuong and not re.search(r"\bsex\b", thuong):
            continue
        # Bỏ phần nhãn rồi mới đọc, để chữ "Nam" trong "Việt Nam" ở cùng
        # dòng không bị hiểu nhầm thành giới tính.
        sau_nhan = re.split(r"(?i)sex|giới tính|gioi tinh", d)[-1]
        sau_nhan = re.split(r"(?i)quốc tịch|quoc tich|nationality", sau_nhan)[0]
        ket_qua = doc(sau_nhan)
        if ket_qua:
            return ket_qua
        for tiep in dong[i + 1:]:
            if _bo_nhieu(tiep):
                return doc(tiep)
    return None


def _tim_quoc_tich(van_ban: str) -> str | None:
    if "viet nam" in _khong_dau(van_ban):
        return "Việt Nam"
    return None


# Từ hay gặp trong địa chỉ Việt Nam, dùng để nhận ra mảnh nào là địa chỉ.
TU_DIA_CHI = (
    "phuong", "xa", "quan", "huyen", "thanh pho", "tinh", "thi tran",
    "duong", "pho", "ngo", "hem", "to", "khu pho", "ap", "thon",
)
# Từ của nhãn, mảnh nào chứa thì không phải nội dung địa chỉ.
TU_NHAN = (
    "place", "residence", "origin", "date", "expiry", "gia tri", "full name",
    "nationality", "sex", "no.", "card", "identity",
    # Chữ in sẵn ở mặt sau thẻ và dấu chứng thực của phường. Không chặn thì
    # những dòng này bị chấm điểm cao vì có dấu phẩy và chữ "quận".
    "hanh chinh", "trat tu", "xa hoi", "canh sat", "cong an", "chung thuc",
    "quyen so", "chu tich", "van phong", "cong chuc", "ngon tro",
    "dac diem", "nhan dang", "ban sao", "ban chinh", "cuc truong",
    "director", "general", "administrative", "management", "index finger",
)


def _ten_rieng(doan: str) -> list[str]:
    """Các từ viết hoa chữ đầu, kiểu tên riêng.

    Không dùng dải ký tự như [A-ZÀ-Ỹ][a-zà-ỹ]+ vì trong bảng mã Unicode,
    dải à-ỹ chứa lẫn cả chữ hoa tiếng Việt như Ề và Đ, khiến rác kiểu "TỀ"
    bị đếm nhầm là tên riêng.
    """
    return [t for t in re.findall(r"[^\W\d_]{2,}", doan)
            if t[0].isupper() and t[1:].islower()]


def _diem_dia_chi(manh: str) -> int:
    """Mảnh càng giống địa chỉ càng nhiều điểm; nhãn và rác bị loại."""
    thuong = _khong_dau(manh)
    if any(t in thuong for t in TU_NHAN):
        return -1
    if len(manh) < 10:
        return -1
    # Quá nhiều ký tự lạ nghĩa là máy đọc hỏng đoạn đó.
    la = sum(1 for c in manh if not (c.isalnum() or c in " ,./-"))
    if la > len(manh) * 0.15:
        return -1
    # Địa chỉ luôn có ít nhất ba tên riêng: đường, phường, quận hoặc tỉnh.
    # Rác máy đọc hiếm khi ghép đủ ba từ viết hoa đúng kiểu.
    ten_rieng = _ten_rieng(manh)
    if len(ten_rieng) < 3:
        return -1
    # Nơi thường trú trên căn cước luôn ngăn cách bằng dấu phẩy. Thiếu dấu
    # phẩy thì gần như chắc chắn là chữ in sẵn chứ không phải địa chỉ.
    if "," not in manh:
        return -1
    diem = manh.count(",") * 3
    diem += sum(2 for t in TU_DIA_CHI if t in thuong)
    diem += len(ten_rieng)
    # Số nhà chỉ vài chữ số; dãy dài hơn gần như luôn là rác dính vào.
    diem -= 4 * len(MAU_SO_DAI.findall(manh))
    return diem


# Đoạn chỉ gồm chữ, khoảng trắng và dấu phẩy: loại được rác lẫn chữ số,
# nhưng cũng cắt mất số nhà.
MAU_DOAN_CHU = re.compile(r"(?:[^\W\d_]|[ ,])+")
# Ký tự lạ dùng làm chỗ cắt: giữ lại được số nhà và tên đường có số.
MAU_KY_TU_LA = re.compile(r"[^\w\sÀ-ỹ,./-]+")
# Dãy bốn chữ số trở lên giữa địa chỉ thường là rác máy đọc nhầm.
MAU_SO_DAI = re.compile(r"(?<!\d)\d{4,}(?!\d)")


def _cat_manh(dong: str) -> list[str]:
    """Cắt một dòng thành ứng viên theo hai cách rồi để bộ chấm điểm chọn.

    Cách chỉ lấy chữ thắng trên ảnh chụp nhiều nhiễu; cách cắt theo ký tự
    lạ thắng trên bản quét sạch, vì giữ được số nhà.
    """
    manh = [m.group(0) for m in MAU_DOAN_CHU.finditer(dong)]
    manh += MAU_KY_TU_LA.split(dong)
    return [x for x in (m.strip(" ,.-") for m in manh) if len(x) >= 10]


def _tim_dia_chi(dong: list[str]) -> str | None:
    """Địa chỉ thường trú hay xuống dòng và lẫn rác, nên chấm điểm từng mảnh.

    Lấy mảnh giống địa chỉ nhất; nếu có mảnh dạng số nhà kèm tên đường ở
    gần đó thì ghép vào phía trước.
    """
    tot_nhat: tuple[int, int, str] | None = None
    for i, d in enumerate(dong):
        for manh in _cat_manh(d):
            diem = _diem_dia_chi(manh)
            if diem > 0 and (tot_nhat is None or diem > tot_nhat[0]):
                tot_nhat = (diem, i, re.sub(r"\s+", " ", manh))
    if tot_nhat is None:
        return None

    diem, chi_so, ket_qua = tot_nhat
    # Địa chỉ dài hay bị xuống dòng giữa chừng, ví dụ "... Thành" rồi dòng
    # sau là "phố Hồ Chí Minh". Dòng nối tiếp luôn bắt đầu bằng chữ thường.
    for tiep in dong[chi_so + 1:]:
        sach = _bo_nhieu(tiep)
        if not sach:
            continue
        if len(sach) <= 40 and sach[0].islower() and not re.search(r"\d{4,}", sach):
            if any(t in _khong_dau(sach) for t in TU_NHAN):
                break
            return f"{ket_qua} {sach}"
        break
    return ket_qua


def tach_truong(van_ban: str) -> dict[str, str | None]:
    """Tách các trường từ văn bản thô. Không chắc thì trả None."""
    dong = [d.strip() for d in van_ban.splitlines() if d.strip()]
    return {
        "identity_number": _tim_so_giay_to(van_ban),
        "full_name": _tim_ten(dong),
        "birth_date": _tim_ngay_sinh(dong),
        "gender": _tim_gioi_tinh(dong),
        "nationality": _tim_quoc_tich(van_ban),
        "permanent_address": _tim_dia_chi(dong),
    }


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


def gop_nhieu_tep(danh_sach: list[bytes]) -> dict:
    """Đọc nhiều tệp rồi gộp lại.

    Mỗi trường lấy giá trị đầu tiên đọc được. Tệp nào không đọc ra gì thì
    không làm hỏng kết quả của tệp khác, vì trường không chắc luôn là null.
    """
    if not danh_sach:
        raise AnhKhongHopLe("Chưa chọn tệp nào")
    if len(danh_sach) > SO_TEP_TOI_DA:
        raise AnhKhongHopLe(
            f"Chỉ nhận tối đa {SO_TEP_TOI_DA} tệp một lần; "
            f"bạn đã chọn {len(danh_sach)}"
        )

    gop: dict[str, str | None] = {ten: None for ten in TRUONG}
    tung_tep = []
    van_ban = []
    loi_cuoi: Exception | None = None

    for thu_tu, du_lieu in enumerate(danh_sach, 1):
        try:
            ket_qua = doc_giay_to(du_lieu)
        except (AnhKhongHopLe, OcrKhongSanSang, RuntimeError) as loi:
            loi_cuoi = loi
            tung_tep.append({"index": thu_tu, "error": str(loi),
                             "recognised": []})
            continue
        for ten, gia_tri in ket_qua["fields"].items():
            if gop[ten] is None and gia_tri:
                gop[ten] = gia_tri
        tung_tep.append({
            "index": thu_tu,
            "source_kind": ket_qua["source_kind"],
            "recognised": ket_qua["recognised"],
        })
        van_ban.append(ket_qua["raw_text"])

    doc_duoc = [ten for ten, gia_tri in gop.items() if gia_tri]
    if not doc_duoc and loi_cuoi is not None:
        raise loi_cuoi

    if doc_duoc:
        canh_bao = (
            "Đây chỉ là gợi ý do máy đọc. Máy thường nhầm dấu tiếng Việt, "
            "nhất là ở họ tên. Đọc lại từng ô trước khi tạo hợp đồng."
        )
    else:
        # Thường gặp với bản photo mờ đem quét lại: chữ xám trên nền xám.
        canh_bao = (
            "Máy không đọc được ô nào. Thường là do tệp quá mờ, ví dụ bản "
            "photo đem quét lại, hoặc thẻ bị nằm ngang trong trang. Hãy chụp "
            "thẳng thẻ bằng điện thoại dưới ánh sáng đều, để thẻ nằm ngay "
            "ngắn và chiếm gần hết khung hình. Hoặc nhập tay các ô bên dưới."
        )

    return {
        "fields": gop,
        "recognised": doc_duoc,
        "missing": [ten for ten in TRUONG if ten not in doc_duoc],
        "is_suggestion_only": True,
        "files": tung_tep,
        "warning": canh_bao,
        "raw_text": "\n".join(van_ban).strip(),
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
