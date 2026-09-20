"""Trích danh mục đơn vị hành chính từ Quyết định 19/2025/QĐ-TTg.

Chạy lại khi có quyết định mới thay thế:

    python tools/trich_don_vi_hanh_chinh.py duong_dan/19_2025_QD-TTg.docx

File .doc cũ phải đổi sang .docx trước:

    soffice --headless --convert-to docx 19_2025_QD-TTg.doc

Cấu trúc văn bản: bảng thứ 3 là danh sách 34 tỉnh thành, các bảng tiếp
theo là danh sách phường xã của từng tỉnh, đúng thứ tự đó.
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
SO_TINH = 34
SO_DON_VI = 3321


def _o(hang) -> list[str]:
    # Chuẩn hóa về NFC: chữ trong file Word ở dạng tổ hợp, nếu để nguyên
    # thì so sánh chuỗi trong Python (vốn viết ở dạng dựng sẵn) sẽ trượt.
    return [
        unicodedata.normalize(
            "NFC", " ".join("".join(c.xpath(".//w:t/text()", namespaces=NS)).split())
        )
        for c in hang.xpath("./w:tc", namespaces=NS)
    ]


def trich(docx: Path) -> dict:
    root = etree.fromstring(ZipFile(docx).read("word/document.xml"))
    bang = root.xpath("//w:tbl", namespaces=NS)
    tinh = [_o(h) for h in bang[2].xpath("./w:tr", namespaces=NS)[1:]]
    if len(tinh) != SO_TINH:
        raise SystemExit(f"Cần {SO_TINH} tỉnh thành, đọc được {len(tinh)}")

    ra: dict = {
        "nguon": "Quyết định 19/2025/QĐ-TTg ngày 30/6/2025 của Thủ tướng "
                 "Chính phủ, hiệu lực từ 01/7/2025",
        "tinh_thanh": [],
        "don_vi": {},
    }
    tong = 0
    for i, (_, ma, ten) in enumerate(tinh):
        hang = bang[3 + i].xpath("./w:tr", namespaces=NS)[1:]
        ten_don_vi = [_o(h)[1] for h in hang]
        if not all(ten_don_vi):
            raise SystemExit(f"Bảng của {ten} có dòng thiếu tên")
        ra["tinh_thanh"].append({"ma": ma, "ten": ten})
        ra["don_vi"][ma] = ten_don_vi
        tong += len(ten_don_vi)

    if tong != SO_DON_VI:
        raise SystemExit(f"Cần {SO_DON_VI} đơn vị cấp xã, đọc được {tong}")
    return ra


if __name__ == "__main__":
    nguon = Path(sys.argv[1])
    dich = Path(__file__).resolve().parent.parent / "config" / "don_vi_hanh_chinh.json"
    du_lieu = trich(nguon)
    dich.write_text(
        json.dumps(du_lieu, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"Đã ghi {dich}: {len(du_lieu['tinh_thanh'])} tỉnh thành, "
          f"{sum(len(v) for v in du_lieu['don_vi'].values())} đơn vị cấp xã.")
