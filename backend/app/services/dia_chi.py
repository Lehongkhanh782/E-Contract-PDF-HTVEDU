"""Viết đầy đủ địa chỉ thay vì viết tắt.

Nhân sự hay gõ tắt: "659, CMT8, P. Hòa hưng, Tphcm". Hợp đồng lao động thì
phải ghi đầy đủ. Ở đây chỉ mở rộng chữ viết tắt và sửa lại cách viết hoa —
không thêm thông tin nào mà người dùng chưa gõ, và không tự đoán tên
phường mới sau sáp nhập, vì đoán sai một cái tên phường trong hợp đồng
còn tệ hơn để nguyên chữ viết tắt.
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache

# Viết tắt của cấp hành chính. Khớp cả khi có dấu chấm và khi không.
CAP_HANH_CHINH = {
    "p": "Phường",
    "q": "Quận",
    "x": "Xã",
    "h": "Huyện",
    "tt": "Thị trấn",
    "tx": "Thị xã",
    "tp": "Thành phố",
    "kp": "Khu phố",
}

# Viết tắt tên riêng và loại đường hay gặp ở hồ sơ nhân sự.
TU_VIET_TAT = {
    "cmt8": "Cách Mạng Tháng Tám",
    "cmt 8": "Cách Mạng Tháng Tám",
    "ctt8": "Cách Mạng Tháng Tám",
    "ql": "Quốc lộ",
    "tl": "Tỉnh lộ",
    "dl": "Đại lộ",
    "đl": "Đại lộ",
    "kdc": "Khu dân cư",
    "kcn": "Khu công nghiệp",
    "cc": "Chung cư",
    "hxh": "Hẻm xe hơi",
}

# Tên tỉnh thành hay bị viết tắt. Chỉ khai những tên mà viết tắt không thể
# nhầm sang thứ khác.
TINH_THANH = {
    "tphcm": "Thành phố Hồ Chí Minh",
    "tp hcm": "Thành phố Hồ Chí Minh",
    "tp.hcm": "Thành phố Hồ Chí Minh",
    "hcm": "Thành phố Hồ Chí Minh",
    "sai gon": "Thành phố Hồ Chí Minh",
    "thanh pho ho chi minh": "Thành phố Hồ Chí Minh",
    "ho chi minh": "Thành phố Hồ Chí Minh",
    "tphn": "Thành phố Hà Nội",
    "tp hn": "Thành phố Hà Nội",
    "ha noi": "Thành phố Hà Nội",
    "tp.hn": "Thành phố Hà Nội",
    "tpdn": "Thành phố Đà Nẵng",
    "da nang": "Thành phố Đà Nẵng",
    "tpct": "Thành phố Cần Thơ",
    "can tho": "Thành phố Cần Thơ",
}

# Những từ giữ chữ thường khi đứng giữa đoạn: "Đường số 33" chứ không phải
# "Đường Số 33". Đứng đầu đoạn thì vẫn viết hoa.
# Viết không dấu vì so sánh bằng bản đã bỏ dấu.
TU_THUONG = {"va", "cua", "so", "hem", "to", "ap", "thon", "lo"}


def _khong_dau(chuoi: str) -> str:
    bo = "".join(
        c for c in unicodedata.normalize("NFD", chuoi.lower())
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", bo).strip()


def _hoa_dau_tu(cum: str) -> str:
    """Viết hoa chữ đầu mỗi từ, giữ nguyên từ vốn đã viết hoa toàn bộ.

    "Hòa hưng" thành "Hòa Hưng", nhưng "TP" hay "II" thì để nguyên vì đó
    thường là viết tắt hoặc số La Mã.
    """
    ra = []
    for thu_tu, tu in enumerate(t for t in cum.split(" ") if t):
        if tu.isupper() and len(tu) > 1:
            # Viết tắt hoặc số La Mã, để nguyên.
            ra.append(tu)
        elif thu_tu > 0 and _khong_dau(tu) in TU_THUONG:
            ra.append(tu.lower())
        else:
            ra.append(tu[0].upper() + tu[1:])
    return " ".join(ra)


def _mo_rong_mot_doan(doan: str) -> str:
    doan = re.sub(r"\s+", " ", doan).strip(" ,.")
    if not doan:
        return ""

    # Tên tỉnh thành xét trước, vì "TP.HCM" và "Thành phố Hồ Chí Minh" đều
    # bắt đầu bằng "TP" nên nếu xét cấp hành chính trước sẽ ra "Thành phố
    # Thành phố Hồ Chí Minh".
    gon = _khong_dau(doan).replace(".", " ")
    gon = re.sub(r"\s+", " ", gon).strip()
    if gon in TINH_THANH:
        return TINH_THANH[gon]

    # Cấp hành chính ở đầu đoạn: "P.10", "P 10", "Q. Tân Bình", "X Hòa Bình".
    khop = re.match(r"^([A-Za-zĐđ]{1,2})\s*\.\s*(.+)$", doan) or re.match(
        r"^([A-Za-zĐđ]{1,2})\s+(\d.*|[A-ZĐ].*)$", doan
    )
    if khop and _khong_dau(khop.group(1)) in CAP_HANH_CHINH:
        cap = CAP_HANH_CHINH[_khong_dau(khop.group(1))]
        return f"{cap} {_mo_rong_mot_doan(khop.group(2))}".strip()

    # Cấp hành chính viết thường nhưng đủ chữ: "phường hòa hưng".
    for viet_tat, day_du in CAP_HANH_CHINH.items():
        dau = _khong_dau(day_du) + " "
        if _khong_dau(doan).startswith(dau):
            con_lai = doan[len(day_du):].strip()
            return f"{day_du} {_mo_rong_mot_doan(con_lai)}".strip()

    # Viết tắt tên riêng, xét theo từng từ để không đụng vào từ khác.
    tu = doan.split(" ")
    ra = []
    for t in tu:
        sach = _khong_dau(t).strip(".,")
        ra.append(TU_VIET_TAT[sach] if sach in TU_VIET_TAT else t)
    return _hoa_dau_tu(" ".join(ra))


# Cấp quận huyện đã bỏ từ 01/7/2025: địa chỉ mới chỉ còn phường xã và
# tỉnh thành. Nhận ra các đoạn này để bỏ đi, nhưng chỉ khi đã chắc chắn
# tìm thấy phường xã hợp lệ trong danh mục chính thức.
CAP_DA_BO = ("Quận", "Huyện", "Thị xã")


@lru_cache(maxsize=1)
def _danh_muc() -> dict:
    """Danh mục đơn vị hành chính chính thức, nạp một lần rồi giữ lại."""
    from app.config import CONFIG_DIR

    duong_dan = CONFIG_DIR / "don_vi_hanh_chinh.json"
    if not duong_dan.is_file():
        return {}
    goc = json.loads(duong_dan.read_text(encoding="utf-8"))

    theo_tinh: dict[str, dict[str, str]] = {}
    for ma, ds in goc["don_vi"].items():
        # Tra theo tên đã bỏ dấu và bỏ chữ Phường/Xã/Thị trấn ở đầu, để
        # người gõ "P. Củ Chi" vẫn tìm ra "Xã Củ Chi".
        theo_tinh[ma] = {_khong_dau(_bo_tien_to(t)): t for t in ds}
    return {
        "tinh": {_khong_dau(t["ten"]): t["ma"] for t in goc["tinh_thanh"]},
        "ten_tinh": {t["ma"]: t["ten"] for t in goc["tinh_thanh"]},
        "don_vi": theo_tinh,
        "nguon": goc["nguon"],
    }


def _bo_tien_to(ten: str) -> str:
    # Về NFC trước khi so, vì chữ lấy từ file Word hay ở dạng tổ hợp.
    ten = unicodedata.normalize("NFC", ten)
    for tien_to in ("Phường", "Xã", "Thị trấn", "Đặc khu"):
        if ten.startswith(tien_to + " "):
            return ten[len(tien_to) + 1:]
    return ten


def viet_day_du(dia_chi: str) -> str:
    """Chỉ mở rộng chữ viết tắt, không đụng tới danh mục hành chính."""
    return chuan_hoa(dia_chi)["address"]


def chuan_hoa(dia_chi: str) -> dict:
    """Viết đầy đủ địa chỉ và quy về danh mục hành chính từ 01/7/2025.

    Trả về địa chỉ đã sửa kèm danh sách lời nhắc. Chỉ bỏ cấp quận huyện
    khi đã tìm thấy phường xã hợp lệ trong danh mục chính thức; tìm không
    ra thì giữ nguyên mọi thứ và nhắc người dùng kiểm tra, chứ không đoán.
    """
    if not dia_chi or not dia_chi.strip():
        return {"address": "", "warnings": []}

    doan = [_mo_rong_mot_doan(d)
            for d in re.split(r"\s*,\s*", dia_chi.strip()) if d.strip()]
    doan = [d for d in doan if d]
    danh_muc = _danh_muc()
    if not danh_muc:
        return {"address": ", ".join(doan), "warnings": []}

    # Tỉnh thành thường ở đoạn cuối; không có thì không quy chiếu được.
    ma_tinh = None
    for i in range(len(doan) - 1, -1, -1):
        ma = danh_muc["tinh"].get(_khong_dau(doan[i]))
        if ma:
            ma_tinh = ma
            doan[i] = danh_muc["ten_tinh"][ma]
            break
    if not ma_tinh:
        return {
            "address": ", ".join(doan),
            "warnings": ["Chưa nhận ra tỉnh thành nên không đối chiếu được "
                         "với danh mục hành chính mới."],
        }

    trong_tinh = danh_muc["don_vi"][ma_tinh]
    vi_tri_phuong = None
    for i, d in enumerate(doan):
        chinh_thuc = trong_tinh.get(_khong_dau(_bo_tien_to(d)))
        if chinh_thuc:
            doan[i] = chinh_thuc
            vi_tri_phuong = i
            break

    nhac: list[str] = []
    if vi_tri_phuong is None:
        nhac.append(
            "Không tìm thấy phường xã nào của địa chỉ này trong danh mục "
            "hành chính từ 01/7/2025. Có thể đây là tên phường cũ đã sáp "
            "nhập — kiểm tra lại trước khi in hợp đồng."
        )
        return {"address": ", ".join(doan), "warnings": nhac}

    # Đã chắc chắn có phường xã hợp lệ thì mới bỏ cấp quận huyện.
    giu = []
    for i, d in enumerate(doan):
        if i != vi_tri_phuong and d.startswith(CAP_DA_BO):
            nhac.append(f"Đã bỏ \"{d}\" vì cấp quận huyện không còn từ "
                        "01/7/2025.")
            continue
        giu.append(d)
    return {"address": ", ".join(giu), "warnings": nhac}
