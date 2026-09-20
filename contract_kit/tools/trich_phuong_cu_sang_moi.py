"""Trích bảng phường xã cũ sang phường xã mới từ file Excel tổng hợp.

    python tools/trich_phuong_cu_sang_moi.py DATABASE_DIA_CHI_DVHC_FINAL.xlsx

Sheet MAPPING_CU_MOI_CLEAN có mỗi dòng là một cặp: xã cũ (kèm huyện cũ và
tỉnh cũ) ứng với xã mới nào.

Một xã cũ có thể rơi vào nhiều xã mới, khi xã đó bị tách ra nhập vào
nhiều nơi. Những trường hợp đó giữ đủ các khả năng chứ không chọn hộ,
để phần dùng sau còn hỏi lại người nhập.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

SHEET = "MAPPING_CU_MOI_CLEAN"
CAP = ("Thành phố", "thành phố", "Tỉnh", "tỉnh", "Phường", "phường",
       "Xã", "xã", "Thị trấn", "thị trấn", "Quận", "quận", "Huyện",
       "huyện", "Thị xã", "thị xã", "Đặc khu", "đặc khu")
# Tên trong file kèm mã trong ngoặc: "Thành phố Hà Nội (01)".
MA_TRONG_NGOAC = re.compile(r"\s*\([^)]*\)\s*$")


def _sach(gia_tri) -> str:
    if gia_tri is None:
        return ""
    return unicodedata.normalize("NFC", " ".join(str(gia_tri).split()))


def _bo_ma(ten: str) -> str:
    return MA_TRONG_NGOAC.sub("", _sach(ten)).strip()


def _khoa(ten: str) -> str:
    """Khóa tra cứu: bỏ mã, bỏ cấp đơn vị, bỏ dấu, viết thường."""
    ten = _bo_ma(ten)
    for cap in CAP:
        if ten.startswith(cap + " "):
            ten = ten[len(cap) + 1:]
            break
    bo = "".join(
        c for c in unicodedata.normalize("NFD", ten.lower())
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", bo).strip()


def trich(xlsx: Path) -> dict:
    import openpyxl

    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    if SHEET not in wb.sheetnames:
        raise SystemExit(f"File không có sheet {SHEET}")
    hang = list(wb[SHEET].iter_rows(min_row=2, values_only=True))

    # tỉnh mới -> xã cũ -> danh sách khả năng
    bang: dict[str, dict[str, list[dict]]] = {}
    bo_qua = 0
    for r in hang:
        tinh_moi, xa_moi, _, xa_cu, _, huyen_cu, _tinh_cu, ghi_chu = r[:8]
        tinh_moi, xa_moi, xa_cu = _bo_ma(tinh_moi), _bo_ma(xa_moi), _bo_ma(xa_cu)
        if not (tinh_moi and xa_moi and xa_cu):
            bo_qua += 1
            continue
        muc = bang.setdefault(_khoa(tinh_moi), {}).setdefault(_khoa(xa_cu), [])
        kha_nang = {
            "xa_moi": xa_moi,
            "tinh_moi": tinh_moi,
            "huyen_cu": _bo_ma(huyen_cu),
            "xa_cu": xa_cu,
            "ghi_chu": _sach(ghi_chu),
        }
        if kha_nang not in muc:
            muc.append(kha_nang)

    tong = sum(len(v) for t in bang.values() for v in t.values())
    mot_kha_nang = sum(1 for t in bang.values() for v in t.values() if len(v) == 1)
    nhieu = sum(1 for t in bang.values() for v in t.values() if len(v) > 1)
    if tong < 10000:
        raise SystemExit(f"Chỉ đọc được {tong} dòng, quá ít so với file gốc")

    return {
        "nguon": "Bảng tổng hợp chuyển đổi địa chỉ hành chính cũ sang mới do "
                 "nhà trường cung cấp (DATABASE_DIA_CHI_DVHC_FINAL.xlsx, "
                 "sheet MAPPING_CU_MOI_CLEAN)",
        "luu_y": "Xã cũ bị tách vào nhiều xã mới thì giữ đủ các khả năng, "
                 "không chọn hộ.",
        "so_cap_cu_moi": tong,
        "so_xa_cu_mot_kha_nang": mot_kha_nang,
        "so_xa_cu_nhieu_kha_nang": nhieu,
        "so_dong_bo_qua": bo_qua,
        "bang": bang,
    }


if __name__ == "__main__":
    du_lieu = trich(Path(sys.argv[1]))
    dich = (Path(__file__).resolve().parent.parent / "config"
            / "phuong_xa_cu_sang_moi.json")
    dich.write_text(json.dumps(du_lieu, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"Đã ghi {dich}")
    print(f"  {du_lieu['so_cap_cu_moi']} cặp cũ-mới")
    print(f"  {du_lieu['so_xa_cu_mot_kha_nang']} xã cũ ra đúng một xã mới")
    print(f"  {du_lieu['so_xa_cu_nhieu_kha_nang']} xã cũ tách ra nhiều xã mới")
