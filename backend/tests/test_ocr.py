"""Kiểm thử đọc ảnh giấy tờ.

Tất cả ảnh dùng ở đây đều do chương trình tự vẽ bằng dữ liệu giả, không
phải giấy tờ của người thật.
"""
from __future__ import annotations

import io
import unittest

from app.services import ocr
from tests import logged_in_client

client = logged_in_client()

CO_TESSERACT = ocr.san_sang()
CO_PDF = ocr.ho_tro_pdf()


def the_gia_pdf(**kwargs) -> bytes:
    """Bản scan PDF chỉ có ảnh, không có lớp chữ, giống máy quét thật."""
    import io

    from PIL import Image

    anh = Image.open(io.BytesIO(ve_the_gia(**kwargs))).convert("RGB")
    bo_nho = io.BytesIO()
    anh.save(bo_nho, format="PDF", resolution=150)
    return bo_nho.getvalue()


def ve_the_gia(ten="NGUYỄN THỊ MINH AN", so="079199000123") -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    thuong = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    dam = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    anh = Image.new("RGB", (1000, 630), (233, 240, 233))
    but = ImageDraw.Draw(anh)
    but.text((300, 40), "CĂN CƯỚC CÔNG DÂN",
             font=ImageFont.truetype(dam, 30), fill=(150, 20, 20))
    dong = [
        ("Số / No.:", so),
        ("Họ và tên / Full name:", ten),
        ("Ngày sinh / Date of birth:", "01/01/1999"),
        ("Giới tính / Sex:", "Nữ"),
        ("Quốc tịch / Nationality:", "Việt Nam"),
        ("Nơi thường trú / Place of residence:",
         "02-04 Đường số 34, Phường An Lạc, TP. Hồ Chí Minh"),
    ]
    y = 110
    for nhan, gia_tri in dong:
        but.text((60, y), nhan, font=ImageFont.truetype(thuong, 19), fill=(60, 60, 60))
        but.text((60, y + 24), gia_tri, font=ImageFont.truetype(dam, 22), fill=(10, 10, 10))
        y += 62
    bo_nho = io.BytesIO()
    anh.save(bo_nho, format="PNG")
    return bo_nho.getvalue()


class TestTachTruong(unittest.TestCase):
    """Tách trường từ văn bản thô, không cần chạy Tesseract."""

    VAN_BAN = (
        "CĂN CƯỚC CÔNG DÂN\n\n"
        "Số /No.:\n\n079199000123\n\n"
        "Họ và tên / Full name:\n\nNGUYÊN THỊ MINH AN\n\n"
        "Ngày sinh / Date of birth:\n\n01/01/1999\n\n"
        "Giới tính / Sex:\n\nNữ\n\n"
        "Quốc tịch / Nationality:\n\nViệt Nam\n\n"
        "Nơi thường trú / Place of residence:\n\n"
        "02-04 Đường số 34, Phường An Lạc, TP. Hồ Chí Minh\n"
    )

    def test_tach_du_sau_truong(self):
        truong = ocr.tach_truong(self.VAN_BAN)
        self.assertEqual(truong["identity_number"], "079199000123")
        self.assertEqual(truong["full_name"], "NGUYÊN THỊ MINH AN")
        self.assertEqual(truong["birth_date"], "1999-01-01")
        self.assertEqual(truong["gender"], "Nữ")
        self.assertEqual(truong["nationality"], "Việt Nam")
        self.assertIn("Đường số 34", truong["permanent_address"])

    def test_ngay_doi_sang_dinh_dang_bieu_mau(self):
        """Thẻ ghi dd/mm/yyyy, biểu mẫu cần yyyy-mm-dd."""
        self.assertEqual(ocr._chuan_hoa_ngay("15/08/1995"), "1995-08-15")
        self.assertEqual(ocr._chuan_hoa_ngay("15-08-1995"), "1995-08-15")

    def test_ngay_khong_hop_le_tra_none(self):
        for xau in ("32/01/1999", "01/13/1999", "khong phai ngay", ""):
            with self.subTest(xau=xau):
                self.assertIsNone(ocr._chuan_hoa_ngay(xau))

    def test_so_giay_to_phai_dung_do_dai(self):
        self.assertEqual(ocr._chuan_hoa_so_giay_to("079 199 000 123"), "079199000123")
        self.assertIsNone(ocr._chuan_hoa_so_giay_to("12345"))
        self.assertIsNone(ocr._chuan_hoa_so_giay_to("0791990001234567"))

    def test_ten_lan_sang_dong_khac_thi_tra_none(self):
        """Tên có chữ số nghĩa là đọc lẫn sang dòng khác; không đoán."""
        self.assertIsNone(ocr._chuan_hoa_ten("NGUYỄN VĂN A 079199"))
        self.assertIsNone(ocr._chuan_hoa_ten(""))

    def test_khong_doc_duoc_thi_tra_none_chu_khong_doan(self):
        truong = ocr.tach_truong("Ảnh mờ không đọc được gì cả")
        self.assertTrue(all(gia_tri is None for gia_tri in truong.values()))

    def test_thieu_mot_truong_van_lay_duoc_cac_truong_con_lai(self):
        van_ban = self.VAN_BAN.replace("NGUYÊN THỊ MINH AN", "")
        truong = ocr.tach_truong(van_ban)
        self.assertEqual(truong["identity_number"], "079199000123")


class TestKiemTraAnh(unittest.TestCase):
    def test_tu_choi_tep_khong_phai_anh(self):
        with self.assertRaises(ocr.AnhKhongHopLe):
            ocr._kiem_tra_anh(b"day khong phai anh")

    def test_tu_choi_tep_rong(self):
        with self.assertRaises(ocr.AnhKhongHopLe):
            ocr._kiem_tra_anh(b"")

    def test_tu_choi_anh_qua_lon(self):
        with self.assertRaises(ocr.AnhKhongHopLe) as bat:
            ocr._kiem_tra_anh(b"x" * (ocr.GIOI_HAN_BYTE + 1))
        self.assertIn("MB", str(bat.exception))

    def test_nhan_anh_png_hop_le(self):
        ocr._kiem_tra_anh(ve_the_gia())


class TestNhanDienPdf(unittest.TestCase):
    def test_nhan_ra_pdf_qua_dau_hieu_dau_tep(self):
        self.assertTrue(ocr.la_pdf(b"%PDF-1.7 ..."))
        self.assertFalse(ocr.la_pdf(b"\x89PNG\r\n"))
        self.assertFalse(ocr.la_pdf(b""))

    def test_tu_choi_pdf_hong(self):
        with self.assertRaises(ocr.AnhKhongHopLe):
            ocr._kiem_tra_pdf(b"%PDF-1.7 nhung khong phai pdf that")

    @unittest.skipUnless(CO_PDF, "Máy chưa cài poppler-utils")
    def test_pdf_mot_trang_duoc_chap_nhan(self):
        self.assertEqual(ocr._kiem_tra_pdf(the_gia_pdf()), 1)

    @unittest.skipUnless(CO_PDF, "Máy chưa cài poppler-utils")
    def test_tu_choi_pdf_qua_nhieu_trang(self):
        import io

        from PIL import Image

        trang = Image.open(io.BytesIO(ve_the_gia())).convert("RGB")
        bo_nho = io.BytesIO()
        trang.save(bo_nho, format="PDF", save_all=True,
                   append_images=[trang] * ocr.SO_TRANG_TOI_DA)
        with self.assertRaises(ocr.AnhKhongHopLe) as bat:
            ocr._kiem_tra_pdf(bo_nho.getvalue())
        self.assertIn("trang", str(bat.exception))


class TestBoNhieu(unittest.TestCase):
    """Máy quét hay thêm gạch hoặc chấm thừa sau nhãn."""

    def test_bo_gach_thua_sau_dau_hai_cham(self):
        van_ban = (
            "Nơi thường trú / Place of residence: -\n"
            "02-04 Đường số 34, Phường An Lạc\n"
        )
        truong = ocr.tach_truong(van_ban)
        self.assertEqual(
            truong["permanent_address"], "02-04 Đường số 34, Phường An Lạc"
        )

    def test_chi_co_nhieu_thi_coi_nhu_trong(self):
        for xau in (" - ", "...", " | ", "~", ""):
            with self.subTest(xau=xau):
                self.assertEqual(ocr._bo_nhieu(xau), "")

    def test_giu_nguyen_noi_dung_that(self):
        self.assertEqual(ocr._bo_nhieu("  Việt Nam  "), "Việt Nam")


class TestApi(unittest.TestCase):
    def test_chua_dang_nhap_thi_bi_chan(self):
        from fastapi.testclient import TestClient

        from app.main import app

        khach = TestClient(app)
        phan_hoi = khach.post("/api/ocr", files={"anh": ("x.png", b"x", "image/png")})
        self.assertEqual(phan_hoi.status_code, 401)

    def test_status_bao_dung_tinh_trang(self):
        body = client.get("/api/ocr/status").json()
        self.assertEqual(body["available"], CO_TESSERACT)
        self.assertEqual(body["pdf"], CO_PDF)
        self.assertEqual(body["fields"], ocr.TRUONG)
        self.assertEqual(body["max_pdf_pages"], ocr.SO_TRANG_TOI_DA)

    def test_tep_khong_phai_anh_bi_tu_choi(self):
        phan_hoi = client.post(
            "/api/ocr", files={"anh": ("a.png", b"khong phai anh", "image/png")}
        )
        self.assertEqual(phan_hoi.status_code, 400)

    @unittest.skipUnless(CO_TESSERACT, "Máy chưa cài Tesseract")
    def test_doc_duoc_the_gia(self):
        phan_hoi = client.post(
            "/api/ocr", files={"anh": ("the.png", ve_the_gia(), "image/png")}
        )
        self.assertEqual(phan_hoi.status_code, 200, phan_hoi.text)
        body = phan_hoi.json()
        self.assertEqual(body["fields"]["identity_number"], "079199000123")
        self.assertEqual(body["fields"]["birth_date"], "1999-01-01")
        self.assertEqual(body["fields"]["gender"], "Nữ")

    @unittest.skipUnless(CO_TESSERACT, "Máy chưa cài Tesseract")
    def test_luon_kem_canh_bao_chi_la_goi_y(self):
        """Không bao giờ được trình bày kết quả OCR như dữ liệu chắc chắn."""
        body = client.post(
            "/api/ocr", files={"anh": ("the.png", ve_the_gia(), "image/png")}
        ).json()
        self.assertTrue(body["is_suggestion_only"])
        self.assertIn("gợi ý", body["warning"])


    @unittest.skipUnless(CO_TESSERACT and CO_PDF, "Thiếu Tesseract hoặc poppler")
    def test_doc_duoc_ban_scan_pdf(self):
        """Bản scan PDF không có lớp chữ vẫn phải đọc được."""
        phan_hoi = client.post(
            "/api/ocr",
            files={"anh": ("scan.pdf", the_gia_pdf(), "application/pdf")},
        )
        self.assertEqual(phan_hoi.status_code, 200, phan_hoi.text)
        body = phan_hoi.json()
        self.assertEqual(body["source_kind"], "pdf")
        self.assertEqual(body["fields"]["identity_number"], "079199000123")
        self.assertEqual(body["fields"]["gender"], "Nữ")
        self.assertEqual(body["fields"]["birth_date"], "1999-01-01")

    @unittest.skipUnless(CO_TESSERACT and CO_PDF, "Thiếu Tesseract hoặc poppler")
    def test_pdf_van_kem_canh_bao_chi_la_goi_y(self):
        body = client.post(
            "/api/ocr",
            files={"anh": ("scan.pdf", the_gia_pdf(), "application/pdf")},
        ).json()
        self.assertTrue(body["is_suggestion_only"])


if __name__ == "__main__":
    unittest.main()
