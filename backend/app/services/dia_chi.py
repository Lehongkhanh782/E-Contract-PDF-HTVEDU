"""Viết địa chỉ đầy đủ và theo đơn vị hành chính có hiệu lực từ 01/7/2025.

Nhân sự hay gõ tắt: "659, CMT8, P. Hòa hưng, Tphcm". Hợp đồng lao động thì
phải ghi đầy đủ và theo tên đơn vị hành chính hiện hành.

Làm bốn việc, theo đúng thứ tự này:

1. Tách cấp hành chính để thêm dấu phẩy, mở rộng chữ viết tắt và sửa cách viết hoa.
2. Đổi tên tỉnh cũ đã hợp nhất sang tỉnh thành mới.
3. Tra tên phường xã trong danh mục mới. Không thấy thì tra tiếp bảng xã
   cũ sang xã mới. Phải theo thứ tự này vì có tên vừa là phường mới có
   thật, vừa là tên một xã cũ ở nơi khác.
4. Bỏ cấp quận huyện, chỉ khi đã chắc chắn có phường xã hợp lệ.

Ba bảng dữ liệu đều trích từ văn bản gốc, xem thư mục contract_kit/tools.

Chỗ nào không chắc thì giữ nguyên và nhắc người nhập, chứ không đoán:
xã cũ bị tách vào nhiều xã mới thì liệt kê các khả năng để người nhập
chọn, vì đoán sai một cái tên phường là sai giấy tờ.
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


def _hoa_mot_tu(tu: str) -> str:
    """Viết hoa một từ đứng giữa đoạn, giữ nguyên từ vốn đã viết hoa hết."""
    if not tu:
        return tu
    if tu.isupper() and len(tu) > 1:
        return tu
    if _khong_dau(tu) in TU_THUONG:
        return tu.lower()
    return tu[0].upper() + tu[1:]


def _mo_rong_mot_doan(doan: str, cho_phep_tinh: bool = True) -> str:
    """Viết đầy đủ một đoạn của địa chỉ.

    cho_phep_tinh=False dùng cho phần còn lại sau khi đã bóc chữ Phường
    hay Xã: nếu vẫn tra tên tỉnh thành ở đó thì "Phường Sài Gòn" sẽ thành
    "Phường Thành phố Hồ Chí Minh", vì Sài Gòn là tên gọi khác của thành
    phố mà cũng là tên một phường có thật.
    """
    doan = re.sub(r"\s+", " ", doan).strip(" ,.")
    if not doan:
        return ""

    # Tên tỉnh thành xét trước, vì "TP.HCM" và "Thành phố Hồ Chí Minh" đều
    # bắt đầu bằng "TP" nên nếu xét cấp hành chính trước sẽ ra "Thành phố
    # Thành phố Hồ Chí Minh".
    gon = _khong_dau(doan).replace(".", " ")
    gon = re.sub(r"\s+", " ", gon).strip()
    if cho_phep_tinh and gon in TINH_THANH:
        return TINH_THANH[gon]

    # Cấp hành chính ở đầu đoạn: "P.10", "P 10", "Q. Tân Bình", "X Hòa Bình".
    khop = re.match(r"^([A-Za-zĐđ]{1,2})\s*\.\s*(.+)$", doan) or re.match(
        r"^([A-Za-zĐđ]{1,2})\s+(\d.*|[A-ZĐ].*)$", doan
    )
    if khop and _khong_dau(khop.group(1)) in CAP_HANH_CHINH:
        cap = CAP_HANH_CHINH[_khong_dau(khop.group(1))]
        con_lai = _mo_rong_mot_doan(khop.group(2), cho_phep_tinh=False)
        return f"{cap} {con_lai}".strip()

    # Cấp hành chính viết thường nhưng đủ chữ: "phường hòa hưng".
    for viet_tat, day_du in CAP_HANH_CHINH.items():
        dau = _khong_dau(day_du) + " "
        if _khong_dau(doan).startswith(dau):
            con_lai = _mo_rong_mot_doan(doan[len(day_du):].strip(),
                                        cho_phep_tinh=False)
            return f"{day_du} {con_lai}".strip()

    # Viết tắt tên riêng, xét theo từng từ để không đụng vào từ khác.
    # Chữ mở rộng ra đã đúng chính tả sẵn nên không viết hoa lại: "ql"
    # thành "Quốc lộ" chứ không phải "Quốc Lộ".
    ra: list[str] = []
    da_co_chu = False
    for t in doan.split(" "):
        sach = _khong_dau(t).strip(".,")
        if sach in TU_VIET_TAT:
            ra.append(TU_VIET_TAT[sach])
            da_co_chu = True
        else:
            ra.append(_hoa_dau_tu(t) if not da_co_chu and not ra
                      else _hoa_mot_tu(t))
    return " ".join(x for x in ra if x)


# Trang tra cứu phường xã sau sáp nhập, để nhân sự bấm vào khi hệ thống
# không nhận ra tên phường. Chỉ dùng làm chỗ cho người tra bằng mắt; dữ
# liệu trong hợp đồng vẫn do người nhập quyết định, không lấy tự động từ
# đây, vì đó không phải nguồn pháp lý.
TRANG_TRA_CUU = "https://vnexpress.net/tra-cuu-xa-phuong-sau-sap-nhap-4908879.html"

# Cấp quận huyện đã bỏ từ 01/7/2025: địa chỉ mới chỉ còn phường xã và
# tỉnh thành. Nhận ra các đoạn này để bỏ đi, nhưng chỉ khi đã chắc chắn
# tìm thấy phường xã hợp lệ trong danh mục chính thức.
# Gồm cả "Thành phố" vì thành phố thuộc tỉnh cũng là cấp huyện; đoạn
# mang tên tỉnh thành được giữ riêng nên không bị nhầm.
CAP_DA_BO = ("Quận", "Huyện", "Thị xã", "Thành phố")

# Tách theo cả dấu phẩy và nhãn hành chính khi người nhập gõ liền địa chỉ.
# Khớp trọn cụm "Thị xã" để không tách thêm một lần ở chữ "xã";
# "Tỉnh lộ" là tên loại đường, không phải nhãn tỉnh.
_NHAN_HANH_CHINH = re.compile(
    r"(?<!\w)(?:"
    r"(?:tp\.?\s*(?:hcm|hn|dn|ct)|hcm)\b"
    r"|(?:"
    r"(?:phường|phuong|xã|xa|quận|quan|huyện|huyen|"
    r"thị\s+trấn|thi\s+tran|thị\s+xã|thi\s+xa|"
    r"thành\s+phố|thanh\s+pho|đặc\s+khu|dac\s+khu)\s+"
    r"|(?:tỉnh|tinh)\s+(?!(?:lộ|lo)\b)"
    r"|(?:tp|tt|tx|p|q|x|h)(?:\.\s*|\s+)"
    r")(?=\w))", re.IGNORECASE,
)


def _tach_doan(dia_chi: str) -> list[str]:
    """Nhận nhãn hành chính dù chưa có dấu phẩy; giữ nguyên phần số/đường."""
    dia_chi = unicodedata.normalize("NFC", dia_chi)
    moc = [m.start() for m in _NHAN_HANH_CHINH.finditer(dia_chi)]
    for vi_tri in reversed(moc):
        if dia_chi[:vi_tri].strip(" ,"):
            dia_chi = dia_chi[:vi_tri] + "," + dia_chi[vi_tri:]
    return [d.strip() for d in dia_chi.split(",") if d.strip()]


def _thu_tp_hcm(doan: list[str], danh_muc: dict) -> str | None:
    """Thiếu tỉnh/thành: ưu tiên TP.HCM khi phường/xã có đối chiếu được.

    Chỉ xét phần cuối địa chỉ (có thể kèm quận/huyện cũ). Không lấy tên
    đường trùng tên phường để suy ra thành phố, không thay tỉnh đã ghi.
    """
    ma = danh_muc["tinh"].get("thanh pho ho chi minh")
    if not ma:
        return None
    # Một tỉnh/thành ghi rõ nhưng không nhận ra cần được kiểm tra lại.
    if any(d.startswith(("Tỉnh ", "Thành phố ")) for d in doan):
        return None
    cac_huyen = {
        _khong_dau(_bo_cap_bat_ky(d))
        for d in doan if d.startswith(CAP_DA_BO)
    }
    trong_tinh = danh_muc["don_vi"][ma]
    bang = _bang_sap_nhap_xa().get("ho chi minh", {})
    for i in range(len(doan) - 1, -1, -1):
        d = doan[i]
        if d.startswith(CAP_DA_BO):
            continue
        # Một tên đứng riêng không có cấp hành chính có thể là tên đường.
        if i == 0 and d == _bo_tien_to(d):
            return None
        khoa = _khong_dau(_bo_tien_to(d))
        if khoa in trong_tinh:
            return ma
        kha_nang = bang.get(khoa, [])
        if cac_huyen:
            kha_nang = [k for k in kha_nang
                         if _khong_dau(_bo_cap_bat_ky(k["huyen_cu"]))
                         in cac_huyen]
        if len(kha_nang) == 1:
            # Bảng cũ phải dẫn về một xã có trong danh mục hiện hành.
            moi = _khong_dau(_bo_tien_to(kha_nang[0]["xa_moi"]))
            if moi in trong_tinh:
                return ma
        return None
    return None


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
    tra_tinh = {_khong_dau(t["ten"]): t["ma"] for t in goc["tinh_thanh"]}
    # Tên tỉnh thành không kèm chữ "Tỉnh"/"Thành phố" cũng phải tra ra.
    for t in goc["tinh_thanh"]:
        tra_tinh.setdefault(_khong_dau(_bo_cap_tinh(t["ten"])), t["ma"])

    # Tỉnh cũ đã hợp nhất: quy về tỉnh thành mới. Ví dụ Bình Dương và Bà
    # Rịa - Vũng Tàu nay thuộc Thành phố Hồ Chí Minh.
    cu_sang_moi: dict[str, str] = {}
    hop_nhat = CONFIG_DIR / "sap_nhap_tinh.json"
    if hop_nhat.is_file():
        bang = json.loads(hop_nhat.read_text(encoding="utf-8"))
        for cu, moi in bang["tinh_cu_sang_moi"].items():
            ma = tra_tinh.get(_khong_dau(_bo_cap_tinh(moi)))
            # Chỉ nhận khi tên mới khớp đúng một tỉnh trong danh mục.
            if ma and _khong_dau(_bo_cap_tinh(cu)) not in tra_tinh:
                cu_sang_moi[_khong_dau(_bo_cap_tinh(cu))] = ma

    return {
        "tinh": tra_tinh,
        "tinh_cu": cu_sang_moi,
        "ten_tinh": {t["ma"]: t["ten"] for t in goc["tinh_thanh"]},
        "don_vi": theo_tinh,
        "nguon": goc["nguon"],
    }


def _bo_cap_tinh(ten: str) -> str:
    ten = unicodedata.normalize("NFC", ten).strip()
    for cap in ("Thành phố ", "thành phố ", "Tỉnh ", "tỉnh "):
        if ten.startswith(cap):
            return ten[len(cap):].strip()
    return ten


@lru_cache(maxsize=1)
def _bang_sap_nhap_xa() -> dict:
    """Bảng xã cũ sang xã mới, nạp một lần rồi giữ lại."""
    from app.config import CONFIG_DIR

    duong_dan = CONFIG_DIR / "phuong_xa_cu_sang_moi.json"
    if not duong_dan.is_file():
        return {}
    return json.loads(duong_dan.read_text(encoding="utf-8"))["bang"]


def _bo_cap_bat_ky(ten: str) -> str:
    """Bỏ mọi tiền tố cấp đơn vị, kể cả cấp quận huyện."""
    ten = unicodedata.normalize("NFC", ten).strip()
    for cap in ("Thành phố ", "Thị trấn ", "Thị xã ", "Đặc khu ",
                "Phường ", "Quận ", "Huyện ", "Tỉnh ", "Xã "):
        if ten.startswith(cap):
            return ten[len(cap):].strip()
    return ten


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
        return {"address": "", "warnings": [], "lookup_url": None}

    doan = [_mo_rong_mot_doan(d) for d in _tach_doan(dia_chi)]
    doan = [d for d in doan if d]
    danh_muc = _danh_muc()
    if not danh_muc:
        return {"address": ", ".join(doan), "warnings": [],
                "lookup_url": None}

    # Tỉnh thành ghi rõ luôn được xét trước quy tắc ưu tiên TP.HCM.
    ma_tinh = None
    vi_tri_tinh = None
    doi_ten_tinh = None
    for i in range(len(doan) - 1, -1, -1):
        khoa = _khong_dau(_bo_cap_tinh(doan[i]))
        ma = danh_muc["tinh"].get(_khong_dau(doan[i])) or danh_muc["tinh"].get(khoa)
        if not ma:
            ma = danh_muc["tinh_cu"].get(khoa)
            if ma:
                doi_ten_tinh = doan[i]
        if ma:
            ma_tinh = ma
            vi_tri_tinh = i
            doan[i] = danh_muc["ten_tinh"][ma]
            break
    bo_sung_tp_hcm = False
    if not ma_tinh:
        ma_tinh = _thu_tp_hcm(doan, danh_muc)
        if ma_tinh:
            bo_sung_tp_hcm = True
            vi_tri_tinh = len(doan)
            doan.append(danh_muc["ten_tinh"][ma_tinh])
    if not ma_tinh:
        return {
            "address": ", ".join(doan),
            "warnings": ["Chưa nhận ra tỉnh thành nên không đối chiếu được "
                         "với danh mục hành chính mới."],
            "lookup_url": None,
        }

    trong_tinh = danh_muc["don_vi"][ma_tinh]
    vi_tri_phuong = None
    for i, d in enumerate(doan):
        chinh_thuc = trong_tinh.get(_khong_dau(_bo_tien_to(d)))
        if chinh_thuc:
            doan[i] = chinh_thuc
            vi_tri_phuong = i
            break

    # Không thấy trong danh mục mới thì tra bảng xã cũ sang xã mới. Phải
    # theo đúng thứ tự này: có những tên như Hòa Hưng vừa là phường mới có
    # thật, vừa là tên một xã cũ ở nơi khác.
    doi_ten_xa = None
    nhieu_kha_nang: list[dict] = []
    if vi_tri_phuong is None:
        bang = _bang_sap_nhap_xa().get(_khong_dau(_bo_cap_bat_ky(
            danh_muc["ten_tinh"][ma_tinh])), {})
        # Đoạn mang cấp quận huyện không phải tên phường, chỉ dùng để loại
        # bớt khả năng. Không tách ra thì "Quận 1" bị tra như xã cũ tên "1".
        cac_huyen = {
            _khong_dau(_bo_cap_bat_ky(x))
            for j, x in enumerate(doan)
            if j != vi_tri_tinh and x.startswith(CAP_DA_BO)
        }
        for i, d in enumerate(doan):
            if i == vi_tri_tinh or d.startswith(CAP_DA_BO):
                continue
            kha_nang = bang.get(_khong_dau(_bo_cap_bat_ky(d)))
            if not kha_nang:
                continue
            thu_hep = [k for k in kha_nang
                       if _khong_dau(_bo_cap_bat_ky(k["huyen_cu"])) in cac_huyen]
            chon = thu_hep or kha_nang
            if len(chon) == 1:
                doi_ten_xa = (d, chon[0]["xa_moi"])
                doan[i] = chon[0]["xa_moi"]
                vi_tri_phuong = i
            else:
                nhieu_kha_nang = chon
            break

    nhac: list[str] = []
    if bo_sung_tp_hcm:
        nhac.append("Đã bổ sung Thành phố Hồ Chí Minh theo phường/xã "
                    "khớp danh mục ưu tiên. Kiểm tra lại địa chỉ trước khi in.")
    if doi_ten_tinh:
        nhac.append(f"Đã đổi \"{doi_ten_tinh}\" thành "
                    f"\"{danh_muc['ten_tinh'][ma_tinh]}\" theo Nghị quyết "
                    "60-NQ/TW về hợp nhất đơn vị hành chính cấp tỉnh.")
    if doi_ten_xa:
        nhac.append(f"Đã đổi \"{doi_ten_xa[0]}\" thành \"{doi_ten_xa[1]}\" "
                    "theo bảng sáp nhập đơn vị hành chính cấp xã.")

    if vi_tri_phuong is None:
        if nhieu_kha_nang:
            # Xã cũ bị tách vào nhiều xã mới; không chọn hộ mà liệt kê ra.
            ds = "; ".join(f"{k['xa_moi']} (phần thuộc {k['huyen_cu']})"
                           for k in nhieu_kha_nang[:6])
            nhac.append(
                "Phường xã cũ này bị tách vào nhiều đơn vị mới nên không tự "
                f"đổi được. Các khả năng: {ds}. Chọn đúng nơi rồi sửa lại ô "
                "địa chỉ."
            )
        else:
            nhac.append(
                "Không tìm thấy phường xã nào của địa chỉ này trong danh mục "
                "hành chính từ 01/7/2025. Có thể đây là tên phường cũ đã sáp "
                "nhập — tra lại rồi sửa cho đúng trước khi in hợp đồng."
            )
        # Chỉ có tên phường cũ mới cần tra; các lỗi khác không cần link.
        return {"address": ", ".join(doan), "warnings": nhac,
                "lookup_url": TRANG_TRA_CUU}

    # Đã chắc chắn có phường xã hợp lệ thì mới bỏ cấp quận huyện.
    giu = []
    for i, d in enumerate(doan):
        if i not in (vi_tri_phuong, vi_tri_tinh) and d.startswith(CAP_DA_BO):
            nhac.append(f"Đã bỏ \"{d}\" vì cấp quận huyện không còn từ "
                        "01/7/2025.")
            continue
        giu.append(d)
    return {"address": ", ".join(giu), "warnings": nhac, "lookup_url": None}
