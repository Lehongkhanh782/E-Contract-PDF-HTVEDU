"""Trích bảng hợp nhất cấp tỉnh từ Nghị quyết 60-NQ/TW.

    python tools/trich_sap_nhap_tinh.py duong_dan/60-NQ_TW.docx

Phụ lục của nghị quyết viết mỗi trường hợp thành một câu:

    16. Hợp nhất tỉnh Bà Rịa - Vũng Tàu, tỉnh Bình Dương và Thành phố Hồ
    Chí Minh; lấy tên là Thành phố Hồ Chí Minh, trung tâm chính trị -
    hành chính đặt tại Thành phố Hồ Chí Minh hiện nay.

Từ đó suy ra tỉnh cũ nào nay thuộc tỉnh thành nào.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
SO_TINH = 34

CAU_HOP_NHAT = re.compile(
    r"^\d+\.\s*Hợp nhất\s+(?P<cu>.+?)[;,]?\s*lấy tên là\s+(?P<moi>.+?)\s*,\s*"
    r"trung tâm",
    re.IGNORECASE,
)
# "tỉnh Bắc Kạn và tỉnh Thái Nguyên" -> hai tên; dấu phẩy và chữ "và".
TACH = re.compile(r"\s*(?:,|;|\bvà\b)\s*")


def _chu(p) -> str:
    return unicodedata.normalize(
        "NFC", " ".join("".join(p.xpath(".//w:t/text()", namespaces=NS)).split())
    )


def _bo_cap(ten: str) -> str:
    """Bỏ chữ tỉnh / thành phố ở đầu để còn lại tên riêng."""
    ten = ten.strip().strip(".;,")
    for cap in ("Thành phố", "thành phố", "Tỉnh", "tỉnh"):
        if ten.startswith(cap + " "):
            return ten[len(cap) + 1:].strip()
    return ten


def trich(docx: Path) -> dict:
    root = etree.fromstring(ZipFile(docx).read("word/document.xml"))
    doan = [_chu(p) for p in root.xpath("//w:p", namespaces=NS)]

    hop_nhat: dict[str, str] = {}
    ten_moi: set[str] = set()
    for d in doan:
        khop = CAU_HOP_NHAT.match(d)
        if not khop:
            continue
        moi = khop.group("moi").strip().strip(".;,")
        ten_moi.add(moi)
        for cu in TACH.split(khop.group("cu")):
            cu = _bo_cap(cu)
            if cu:
                hop_nhat[cu] = moi

    if not hop_nhat:
        raise SystemExit("Không đọc được câu hợp nhất nào; kiểm tra lại file")

    # Phần I của phụ lục liệt kê các tỉnh không sáp nhập. Cộng với số
    # trường hợp hợp nhất phải ra đúng 34, nếu không là đọc sót.
    giu_nguyen = _phan_giu_nguyen(doan)
    if len(giu_nguyen) + len(ten_moi) != SO_TINH:
        raise SystemExit(
            f"Đọc được {len(giu_nguyen)} tỉnh giữ nguyên và {len(ten_moi)} "
            f"tỉnh sau hợp nhất, cộng lại không ra {SO_TINH}"
        )

    return {
        "nguon": "Nghị quyết 60-NQ/TW ngày 12/4/2025 Hội nghị lần thứ 11 "
                 "Ban Chấp hành Trung ương Đảng khóa XIII",
        "so_truong_hop_hop_nhat": len(ten_moi),
        "tinh_giu_nguyen": giu_nguyen,
        "tinh_cu_sang_moi": dict(sorted(hop_nhat.items())),
    }


def _phan_giu_nguyen(doan: list[str]) -> list[str]:
    """Các tỉnh thành ở phần I của phụ lục: không thực hiện sáp nhập."""
    try:
        dau = next(i for i, d in enumerate(doan)
                   if d.startswith("I- Các đơn vị"))
        cuoi = next(i for i, d in enumerate(doan)
                    if d.startswith("II- Các đơn vị"))
    except StopIteration:
        raise SystemExit("Không tìm thấy phần I và II của phụ lục") from None
    ra = []
    for d in doan[dau + 1:cuoi]:
        khop = re.match(r"^\d+\.\s*(.+?)\.?$", d)
        if khop:
            ra.append(khop.group(1).strip())
    return ra


if __name__ == "__main__":
    du_lieu = trich(Path(sys.argv[1]))
    dich = Path(__file__).resolve().parent.parent / "config" / "sap_nhap_tinh.json"
    dich.write_text(
        json.dumps(du_lieu, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"Đã ghi {dich}: {du_lieu['so_truong_hop_hop_nhat']} trường hợp hợp "
          f"nhất, {len(du_lieu['tinh_cu_sang_moi'])} tên tỉnh cũ.")
