"""Kiểm tra bố cục của một PDF đã dựng.

Chạy sau khi tạo PDF để chắc rằng bản in hai mặt tách tờ được và mức bồi
thường đúng theo đơn vị.

    python kiem_tra_bo_cuc.py out/victoria.pdf --unit victoria
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from generate_demo import doc_so_tien, load_json, money
from decimal import Decimal

ROOT = Path(__file__).resolve().parent

# Mỗi phần phải bắt đầu ở mặt trước của một tờ mới, tức trang lẻ.
DAU_PHAN = {
    "Hợp đồng lao động": "HỢP ĐỒNG LAO ĐỘNG",
    "Phụ lục lương": "PHỤ LỤC HỢP ĐỒNG",
    "Thỏa thuận trách nhiệm": "THỎA THUẬN",
}


def kiem_tra(pdf: Path, unit_id: str) -> list[str]:
    from pypdf import PdfReader

    loi: list[str] = []
    reader = PdfReader(pdf)
    trang = [(p.extract_text() or "") for p in reader.pages]

    # 1. Mỗi phần bắt đầu ở trang lẻ
    for ten, dau_hieu in DAU_PHAN.items():
        vi_tri = [i + 1 for i, t in enumerate(trang) if dau_hieu in t.upper()]
        if not vi_tri:
            loi.append(f"Không tìm thấy phần {ten!r} (dấu hiệu {dau_hieu!r})")
            continue
        if vi_tri[0] % 2 == 0:
            loi.append(
                f"Phần {ten!r} bắt đầu ở trang {vi_tri[0]} là trang chẵn, "
                "tức mặt sau của tờ trước; không bấm riêng được"
            )

    # 2. Trang trống phải thật sự trống, chỉ có ghi chú
    for i, t in enumerate(trang, 1):
        sach = re.sub(r"\s+", " ", t).strip()
        if "(Trang này để trống)" in sach:
            con_lai = sach.replace("(Trang này để trống)", "")
            con_lai = con_lai.replace("BẢN THỬ NGHIỆM - DỮ LIỆU GIẢ - CHƯA DÙNG KÝ", "")
            if con_lai.strip():
                loi.append(f"Trang {i} đáng lẽ để trống nhưng còn nội dung")

    # 3. Mức bồi thường đúng theo đơn vị
    units = {u["unit_id"]: u for u in load_json(ROOT / "config/units.json")["units"]}
    if unit_id not in units:
        loi.append(f"Đơn vị {unit_id} không có trong cấu hình")
    else:
        so = units[unit_id]["liability_amount"]
        mong_doi = f"{money(Decimal(so))} VNĐ ({doc_so_tien(so)})"
        toan_van = re.sub(r"\s+", " ", " ".join(trang))
        if mong_doi not in toan_van:
            loi.append(f"Không thấy mức bồi thường đúng: cần {mong_doi!r}")

    # 4. Không sót biến chưa điền
    if "{{" in " ".join(trang) or "}}" in " ".join(trang):
        loi.append("PDF còn sót biến chưa điền dạng {{ ... }}")

    return loi


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--unit", required=True)
    args = parser.parse_args()

    loi = kiem_tra(args.pdf, args.unit)
    if loi:
        print(f"KHÔNG ĐẠT: {args.pdf}")
        for dong in loi:
            print(f"  - {dong}")
        sys.exit(1)
    print(f"Đạt: {args.pdf.name} ({args.unit})")


if __name__ == "__main__":
    main()
