"""Kiểm thử bố cục in hai mặt và mức bồi thường theo đơn vị.

Hợp đồng, phụ lục lương và thỏa thuận được bấm thành ba tập riêng nên mỗi
phần phải bắt đầu ở mặt trước của một tờ mới, tức là ở trang lẻ.
"""
from __future__ import annotations

import json
import unittest
from decimal import Decimal
from pathlib import Path

from generate_demo import (
    build_context,
    can_thoa_thuan,
    doc_so_tien,
    load_json,
    money,
)

ROOT = Path(__file__).resolve().parent


def ho_so_thu() -> dict:
    return load_json(ROOT / "examples/employee_demo.json")


def chinh_sach() -> dict:
    return load_json(ROOT / "config/salary_policy_example.json")


class TestDocSoTien(unittest.TestCase):
    def test_cac_muc_boi_thuong_dang_dung(self):
        self.assertEqual(doc_so_tien(20000000), "hai mươi triệu đồng")
        self.assertEqual(doc_so_tien(10000000), "mười triệu đồng")

    def test_quy_tac_doc_dac_biet(self):
        # mười lăm chứ không phải mười năm; hai mươi mốt chứ không phải hai
        # mươi một; hai mươi tư chứ không phải hai mươi bốn.
        self.assertEqual(doc_so_tien(15000000), "mười lăm triệu đồng")
        self.assertEqual(doc_so_tien(21000000), "hai mươi mốt triệu đồng")
        self.assertEqual(doc_so_tien(24000000), "hai mươi tư triệu đồng")

    def test_so_khong_o_giua(self):
        self.assertEqual(doc_so_tien(101), "một trăm linh một đồng")
        self.assertEqual(doc_so_tien(1005), "một nghìn không trăm linh năm đồng")

    def test_so_tien_trong_phu_luc(self):
        self.assertEqual(
            doc_so_tien(5389350),
            "năm triệu ba trăm tám mươi chín nghìn ba trăm năm mươi đồng",
        )

    def test_khong_nhan_so_am(self):
        with self.assertRaises(ValueError):
            doc_so_tien(-1)

    def test_bao_loi_khi_vuot_pham_vi(self):
        with self.assertRaises(ValueError):
            doc_so_tien(10**15)


class TestMucBoiThuongTheoDonVi(unittest.TestCase):
    MUC = {
        "vuon_sang_tao": "20000000",
        "victoria": "20000000",
        "gau_panda": "10000000",
        "dai_duong_xanh": "20000000",
    }

    def test_cau_hinh_du_bon_don_vi(self):
        units = load_json(ROOT / "config/units.json")["units"]
        thuc_te = {u["unit_id"]: u["liability_amount"] for u in units}
        self.assertEqual(thuc_te, self.MUC)

    def test_context_dien_dung_muc_cua_tung_don_vi(self):
        for unit_id, so_tien in self.MUC.items():
            with self.subTest(unit=unit_id):
                context, _ = build_context(unit_id, ho_so_thu(), chinh_sach())
                phan = context["responsibility"]
                self.assertEqual(phan["liability_amount"], money(Decimal(so_tien)))
                self.assertEqual(phan["liability_amount_words"], doc_so_tien(so_tien))

    def test_gau_panda_khac_cac_don_vi_con_lai(self):
        panda, _ = build_context("gau_panda", ho_so_thu(), chinh_sach())
        khac, _ = build_context("victoria", ho_so_thu(), chinh_sach())
        self.assertEqual(panda["responsibility"]["liability_amount"], "10.000.000")
        self.assertEqual(khac["responsibility"]["liability_amount"], "20.000.000")

    def test_thieu_cau_hinh_thi_bao_loi(self):
        """Không được tự đoán mức bồi thường khi cấu hình thiếu."""
        import generate_demo

        goc = generate_demo.load_json

        def gia(path):
            data = goc(path)
            if path.name == "units.json":
                for unit in data["units"]:
                    unit.pop("liability_amount", None)
            return data

        generate_demo.load_json = gia
        try:
            with self.assertRaises(ValueError) as bat:
                build_context("victoria", ho_so_thu(), chinh_sach())
            self.assertIn("liability_amount", str(bat.exception))
        finally:
            generate_demo.load_json = goc

    def test_mau_word_khong_con_so_ghi_cung(self):
        from zipfile import ZipFile

        from lxml import etree

        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        mau = ROOT / "templates/Thoa_thuan_trach_nhiem_template.docx"
        with ZipFile(mau) as z:
            root = etree.fromstring(z.read("word/document.xml"))
        text = "".join(root.xpath("//w:t/text()", namespaces=ns))
        self.assertNotIn("20.000.000", text)
        self.assertIn("{{ responsibility.liability_amount }}", text)
        self.assertIn("{{ responsibility.liability_amount_words }}", text)


class TestAiPhaiKyThoaThuan(unittest.TestCase):
    """Chỉ người trực tiếp dạy và trông trẻ mới kèm thỏa thuận trách nhiệm."""

    CAN_KY = {
        "principal": False,
        "preschool_teacher": True,
        "english_teacher": True,
        "nanny": True,
        "admissions_marketing": False,
    }

    def test_cau_hinh_khai_du_nam_vi_tri(self):
        rules = load_json(ROOT / "config/business_rules.json")["positions"]
        thuc_te = {p["position_id"]: p["requires_responsibility_agreement"]
                   for p in rules}
        self.assertEqual(thuc_te, self.CAN_KY)

    def test_ham_tra_dung_cho_tung_vi_tri(self):
        for position_id, mong_doi in self.CAN_KY.items():
            with self.subTest(vi_tri=position_id):
                self.assertEqual(
                    can_thoa_thuan({"job": {"position_id": position_id}}),
                    mong_doi,
                )

    def test_thieu_co_trong_cau_hinh_thi_bao_loi(self):
        import generate_demo

        goc = generate_demo.load_json

        def gia(path):
            data = goc(path)
            if path.name == "business_rules.json":
                for vi_tri in data["positions"]:
                    vi_tri.pop("requires_responsibility_agreement", None)
            return data

        generate_demo.load_json = gia
        try:
            with self.assertRaises(ValueError) as bat:
                can_thoa_thuan({"job": {"position_id": "nanny"}})
            self.assertIn("requires_responsibility_agreement", str(bat.exception))
        finally:
            generate_demo.load_json = goc


class TestNoiLamViec(unittest.TestCase):
    """Nơi làm việc tách khỏi địa chỉ đăng ký kinh doanh."""

    def test_victoria_lam_viec_o_dia_chi_khac(self):
        units = {u["unit_id"]: u
                 for u in load_json(ROOT / "config/units.json")["units"]}
        vic = units["victoria"]
        self.assertNotEqual(vic["workplace_address"], vic["address"])
        self.assertEqual(
            vic["workplace_institution_name"], "Trường Mầm non Ngôi Nhà Ánh Dương"
        )
        self.assertIn("Đường số 33", vic["workplace_address"])
        # Pháp nhân ký hợp đồng vẫn là Victoria.
        self.assertIn("VICTORIA", vic["legal_name"])

    def test_ba_don_vi_con_lai_lam_viec_tai_dia_chi_dang_ky(self):
        units = load_json(ROOT / "config/units.json")["units"]
        for unit in units:
            if unit["unit_id"] == "victoria":
                continue
            with self.subTest(unit=unit["unit_id"]):
                self.assertEqual(unit["workplace_address"], unit["address"])
                self.assertEqual(
                    unit["workplace_institution_name"], unit["institution_name"]
                )

    def test_moi_don_vi_deu_khai_du_noi_lam_viec(self):
        for unit in load_json(ROOT / "config/units.json")["units"]:
            with self.subTest(unit=unit["unit_id"]):
                self.assertTrue(unit.get("workplace_address"))
                self.assertTrue(unit.get("workplace_institution_name"))

    def test_context_dien_noi_lam_viec_chu_khong_phai_dia_chi_dang_ky(self):
        context, _ = build_context("victoria", ho_so_thu(), chinh_sach())
        employer = context["employer"]
        self.assertEqual(
            employer["workplace_institution_name"],
            "Trường Mầm non Ngôi Nhà Ánh Dương",
        )
        self.assertNotEqual(employer["workplace_address"], employer["address"])

    def test_mau_hop_dong_dung_bien_noi_lam_viec(self):
        from zipfile import ZipFile

        from lxml import etree

        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        mau = ROOT / "templates/Hop_dong_va_phu_luc_template.docx"
        with ZipFile(mau) as z:
            root = etree.fromstring(z.read("word/document.xml"))
        text = "".join(root.xpath("//w:t/text()", namespaces=ns))
        self.assertIn(
            "{{ employer.workplace_institution_name }} tại địa chỉ "
            "{{ employer.workplace_address }}",
            text,
        )
        # Khối bên sử dụng lao động vẫn dùng địa chỉ đăng ký.
        self.assertIn("Địa chỉ: {{ employer.address }}", text)


class TestBanDoTruong(unittest.TestCase):
    def test_cac_bien_moi_co_trong_ban_do(self):
        d = load_json(ROOT / "config/field_map.json")
        ten = {f["field"] for f in d["fields"]}
        for bien in ("responsibility.liability_amount",
                     "responsibility.liability_amount_words",
                     "employer.workplace_address",
                     "employer.workplace_institution_name"):
            with self.subTest(bien=bien):
                self.assertIn(bien, ten)


if __name__ == "__main__":
    unittest.main()
