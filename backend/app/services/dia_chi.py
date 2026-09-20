"""Viết đầy đủ địa chỉ thay vì viết tắt.

Nhân sự hay gõ tắt: "659, CMT8, P. Hòa hưng, Tphcm". Hợp đồng lao động thì
phải ghi đầy đủ. Ở đây chỉ mở rộng chữ viết tắt và sửa lại cách viết hoa —
không thêm thông tin nào mà người dùng chưa gõ, và không tự đoán tên
phường mới sau sáp nhập, vì đoán sai một cái tên phường trong hợp đồng
còn tệ hơn để nguyên chữ viết tắt.
"""
from __future__ import annotations

import re
import unicodedata

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


def viet_day_du(dia_chi: str) -> str:
    """Mở rộng chữ viết tắt trong địa chỉ và sửa lại cách viết hoa.

    Không thêm thông tin người dùng chưa gõ, không bỏ bớt phần nào, và
    không đổi tên phường xã theo đợt sáp nhập.
    """
    if not dia_chi or not dia_chi.strip():
        return ""
    doan = [d for d in re.split(r"\s*,\s*", dia_chi.strip()) if d.strip()]
    ket_qua = [_mo_rong_mot_doan(d) for d in doan]
    return ", ".join(d for d in ket_qua if d)
