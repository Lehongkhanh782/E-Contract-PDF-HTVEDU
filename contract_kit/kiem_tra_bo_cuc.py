"""Kiểm tra bố cục của một PDF đã dựng.

Chạy sau khi tạo PDF để chắc rằng bản in hai mặt tách tờ được, đúng thành
phần theo vị trí, và mức bồi thường đúng theo đơn vị.

    python kiem_tra_bo_cuc.py out/victoria.pdf --unit victoria \
        --position english_teacher
"""
from __future__ import annotations

import argparse
import re
import sys
from decimal import Decimal
from pathlib import Path

from generate_demo import doc_so_tien, load_json, money

ROOT = Path(__file__).resolve().parent

# Dấu hiệu phải là chuỗi chỉ xuất hiện đúng ở trang mở đầu mỗi phần.
# Không dùng tiêu đề chung chung: chữ "thỏa thuận" có mặt trên mọi trang
# hợp đồng nên không nhận dạng được tờ Thỏa thuận trách nhiệm.
DAU_PHAN = {
    "Hợp đồng lao động": "/HDLD/",
    "Phụ lục lương": "PHỤ LỤC HỢP ĐỒNG",
    "Thỏa thuận trách nhiệm": "/TT/",
}
GHI_CHU_TRANG_TRONG = "(Trang này để trống)"
DONG_DANH_DAU = "BẢN THỬ NGHIỆM - DỮ LIỆU GIẢ - CHƯA DÙNG KÝ"


def _can_thoa_thuan(position_id: str) -> bool:
    rules = load_json(ROOT / "config/business_rules.json")["positions"]
    khop = [p for p in rules if p["position_id"] == position_id]
    if len(khop) != 1:
        raise SystemExit(f"Vị trí {position_id} không có trong cấu hình")
    return bool(khop[0]["requires_responsibility_agreement"])


def kiem_tra(pdf: Path, unit_id: str, position_id: str) -> list[str]:
    from pypdf import PdfReader

    loi: list[str] = []
    trang = [(p.extract_text() or "") for p in PdfReader(pdf).pages]
    toan_van = re.sub(r"\s+", " ", " ".join(trang))
    kem_thoa_thuan = _can_thoa_thuan(position_id)

    can_co = {
        "Hợp đồng lao động": True,
        "Phụ lục lương": True,
        "Thỏa thuận trách nhiệm": kem_thoa_thuan,
    }

    for ten, dau_hieu in DAU_PHAN.items():
        vi_tri = [i + 1 for i, t in enumerate(trang) if dau_hieu in t]
        if not can_co[ten]:
            if vi_tri:
                loi.append(
                    f"Vị trí {position_id} không phải ký {ten!r} "
                    f"nhưng PDF vẫn có ở trang {vi_tri[0]}"
                )
            continue
        if not vi_tri:
            loi.append(f"Thiếu phần {ten!r} (dấu hiệu {dau_hieu!r})")
            continue
        if len(vi_tri) > 1:
            loi.append(
                f"Dấu hiệu {dau_hieu!r} của phần {ten!r} xuất hiện ở "
                f"{len(vi_tri)} trang; không nhận dạng chắc chắn được"
            )
            continue
        # Mỗi phần phải bắt đầu ở mặt trước của một tờ mới, tức trang lẻ.
        if vi_tri[0] % 2 == 0:
            loi.append(
                f"Phần {ten!r} bắt đầu ở trang {vi_tri[0]} là trang chẵn, "
                "tức mặt sau của tờ trước; không bấm riêng được"
            )

    for i, t in enumerate(trang, 1):
        sach = re.sub(r"\s+", " ", t).strip()
        if GHI_CHU_TRANG_TRONG in sach:
            con_lai = sach.replace(GHI_CHU_TRANG_TRONG, "").replace(DONG_DANH_DAU, "")
            if con_lai.strip():
                loi.append(f"Trang {i} đáng lẽ để trống nhưng còn nội dung")

    units = {u["unit_id"]: u for u in load_json(ROOT / "config/units.json")["units"]}
    if unit_id not in units:
        loi.append(f"Đơn vị {unit_id} không có trong cấu hình")
    else:
        unit = units[unit_id]
        if kem_thoa_thuan:
            so = unit["liability_amount"]
            mong_doi = f"{money(Decimal(so))} VNĐ ({doc_so_tien(so)})"
            if mong_doi not in toan_van:
                loi.append(f"Không thấy mức bồi thường đúng: cần {mong_doi!r}")
        # Nơi làm việc phải là địa chỉ làm việc, không phải địa chỉ đăng ký.
        if unit["workplace_address"] not in toan_van:
            loi.append(
                f"Không thấy địa chỉ nơi làm việc {unit['workplace_address']!r}"
            )
        if unit["workplace_institution_name"] not in toan_van:
            loi.append(
                "Không thấy tên nơi làm việc "
                f"{unit['workplace_institution_name']!r}"
            )

    if "{{" in toan_van or "}}" in toan_van:
        loi.append("PDF còn sót biến chưa điền dạng {{ ... }}")

    return loi


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--unit", required=True)
    parser.add_argument("--position", required=True)
    args = parser.parse_args()

    loi = kiem_tra(args.pdf, args.unit, args.position)
    if loi:
        print(f"KHÔNG ĐẠT: {args.pdf}")
        for dong in loi:
            print(f"  - {dong}")
        sys.exit(1)
    print(f"Đạt: {args.pdf.name} ({args.unit} / {args.position})")


if __name__ == "__main__":
    main()
