"""Kiểm thử viết đầy đủ địa chỉ.

Nguyên tắc: chỉ mở rộng chữ viết tắt và sửa cách viết hoa. Không thêm
thông tin người dùng chưa gõ, không bỏ bớt phần nào, và không đổi tên
phường xã theo đợt sáp nhập.
"""
from __future__ import annotations

import unittest

from app.services.dia_chi import chuan_hoa, viet_day_du
from tests import logged_in_client

client = logged_in_client()


class TestVietDayDu(unittest.TestCase):

    def test_dung_vi_du_anh_khanh_gui(self):
        self.assertEqual(
            viet_day_du("659, CMT8, P. Hòa hưng, Tphcm"),
            "659, Cách Mạng Tháng Tám, Phường Hòa Hưng, "
            "Thành phố Hồ Chí Minh",
        )

    def test_cac_cap_hanh_chinh_viet_tat(self):
        self.assertEqual(
            viet_day_du("số 5, KP 3, TT. Củ Chi, tphcm"),
            # Danh mục mới ghi là Xã Củ Chi, không còn Thị trấn.
            "Số 5, Khu phố 3, Xã Củ Chi, Thành phố Hồ Chí Minh",
        )
        self.assertEqual(
            viet_day_du("x. Hòa bình, h. Trà ôn, Vĩnh Long"),
            "Xã Hòa Bình, Huyện Trà Ôn, Vĩnh Long",
        )

    def test_phuong_quan_co_so(self):
        self.assertEqual(viet_day_du("12 Lê Lợi, Q.1, TP.HCM"),
                         "12 Lê Lợi, Quận 1, Thành phố Hồ Chí Minh")
        self.assertEqual(viet_day_du("P.10"), "Phường 10")

    def test_khong_nhan_doi_thanh_pho(self):
        """TP.HCM và Thành phố Hồ Chí Minh đều bắt đầu bằng TP."""
        for xau in ("TP.HCM", "TP HCM", "tphcm", "Thành phố Hồ Chí Minh",
                    "Hồ Chí Minh", "hcm"):
            self.assertEqual(viet_day_du(xau), "Thành phố Hồ Chí Minh", xau)

    def test_sua_cach_viet_hoa_va_bo_sung_chu_phuong(self):
        self.assertEqual(viet_day_du("32/11 đường 13A, bình hưng hòa, HCM"),
                         "32/11 Đường 13A, Phường Bình Hưng Hòa, "
                         "Thành phố Hồ Chí Minh")

    def test_tu_so_khong_viet_hoa_giua_doan(self):
        self.assertEqual(viet_day_du("1/4 Đường số 33, Phường An Khánh"),
                         "1/4 Đường số 33, Phường An Khánh")

    def test_dia_chi_da_day_du_thi_chi_sua_chinh_ta(self):
        self.assertEqual(
            viet_day_du("946/6 Tân Kỳ Tân Quý, Phường Bình Hưng Hoà, "
                        "Thành phố Hồ Chí Minh"),
            "946/6 Tân Kỳ Tân Quý, Phường Bình Hưng Hòa, "
            "Thành phố Hồ Chí Minh",
        )

    def test_khong_tu_doi_ten_phuong(self):
        """Tên phường giữ nguyên, chỉ quy về đúng chính tả trong danh mục."""
        ra = viet_day_du("P. Hòa Hưng, TPHCM")
        self.assertIn("Phường Hòa Hưng", ra)

    def test_o_trong_thi_tra_ve_trong(self):
        for xau in ("", "   ", None):
            self.assertEqual(viet_day_du(xau), "")

    def test_chu_la_thi_giu_nguyen_chu_khong_bia(self):
        self.assertEqual(viet_day_du("Ấp Bảy Ngàn, Hậu Giang"),
                         "Ấp Bảy Ngàn, Hậu Giang")

    def test_thua_dau_phay_va_khoang_trang(self):
        self.assertEqual(viet_day_du("  12  Lê Lợi ,, Q.1 ,  "),
                         "12 Lê Lợi, Quận 1")

    def test_khong_bo_bot_phan_nao(self):
        ra = viet_day_du("659, CMT8, P. Hòa hưng, Tphcm")
        self.assertEqual(ra.count(","), 3)


class TestDanhMucHanhChinh(unittest.TestCase):
    """Quy địa chỉ về danh mục hành chính có hiệu lực từ 01/7/2025.

    Danh mục lấy từ Quyết định 19/2025/QĐ-TTg, không phải nguồn tự đoán.
    """

    def test_bo_cap_quan_huyen_khi_phuong_hop_le(self):
        ra = chuan_hoa("số 7, P. Củ Chi, huyện Củ Chi, tphcm")
        self.assertEqual(ra["address"],
                         "Số 7, Xã Củ Chi, Thành phố Hồ Chí Minh")
        self.assertTrue(any("quận huyện" in n for n in ra["warnings"]))

    def test_sua_phuong_thanh_xa_theo_danh_muc(self):
        """Củ Chi nay là Xã chứ không phải Phường."""
        self.assertIn("Xã Củ Chi", chuan_hoa("P. Củ Chi, tphcm")["address"])

    def test_sua_chinh_ta_theo_danh_muc(self):
        """Hoà và Hòa là hai cách gõ khác nhau; lấy đúng bản trong danh mục."""
        ra = chuan_hoa("P Bình Hưng Hoà, Thành phố Hồ Chí Minh")
        self.assertIn("Phường Bình Hưng Hòa", ra["address"])
        self.assertEqual(ra["warnings"], [])

    def test_phuong_cu_da_sap_nhap_thi_nhac_chu_khong_doan(self):
        """Bến Nghé không còn trong danh mục mới."""
        ra = chuan_hoa("12 Lê Lợi, Phường Bến Nghé, Quận 1, TP.HCM")
        self.assertIn("Phường Bến Nghé", ra["address"])
        self.assertIn("Quận 1", ra["address"])
        self.assertTrue(any("sáp nhập" in n for n in ra["warnings"]))

    def test_khong_bo_quan_huyen_khi_chua_chac_phuong(self):
        """Chưa xác nhận được phường thì giữ nguyên hết, không cắt bớt."""
        ra = chuan_hoa("12 Lê Lợi, Phường Bến Nghé, Quận 1, TP.HCM")
        self.assertIn("Quận 1", ra["address"])
        self.assertIn("Phường Bến Nghé", ra["address"])

    def test_chi_ghi_quan_ma_khong_ghi_phuong_thi_nhac(self):
        """Quận Tân Bình không phải phường, dù có Phường Tân Bình mới."""
        ra = chuan_hoa("5 Nguyễn Trãi, Quận Tân Bình, TPHCM")
        self.assertIn("Quận Tân Bình", ra["address"])
        self.assertTrue(any("sáp nhập" in n for n in ra["warnings"]))

    def test_khong_nhan_ra_tinh_thi_nhac(self):
        ra = chuan_hoa("12 Lê Lợi, Phường Nào Đó")
        self.assertTrue(any("tỉnh thành" in n for n in ra["warnings"]))

    def test_dia_chi_dung_thi_khong_nhac_gi(self):
        for x in ("659, CMT8, P. Hòa hưng, Tphcm",
                  "17 Bùi Huy Bích, phường Phú Định, TPHCM",
                  "1/4 Đường số 33, P. An Khánh, TP HCM"):
            self.assertEqual(chuan_hoa(x)["warnings"], [], x)


class TestFileDanhMuc(unittest.TestCase):
    """Chốt tính toàn vẹn của file danh mục trích từ văn bản gốc."""

    def setUp(self):
        import json

        from app.config import CONFIG_DIR

        self.goc = json.loads(
            (CONFIG_DIR / "don_vi_hanh_chinh.json").read_text(encoding="utf-8")
        )

    def test_du_34_tinh_thanh(self):
        self.assertEqual(len(self.goc["tinh_thanh"]), 34)

    def test_du_3321_don_vi_cap_xa(self):
        tong = sum(len(v) for v in self.goc["don_vi"].values())
        self.assertEqual(tong, 3321)

    def test_ghi_ro_nguon(self):
        self.assertIn("19/2025/QĐ-TTg", self.goc["nguon"])

    def test_moi_tinh_deu_co_danh_sach(self):
        for t in self.goc["tinh_thanh"]:
            self.assertTrue(self.goc["don_vi"].get(t["ma"]), t["ten"])


class TestApiDiaChi(unittest.TestCase):

    def test_chua_dang_nhap_thi_bi_chan(self):
        from fastapi.testclient import TestClient

        from app.main import app

        r = TestClient(app).post("/api/address", json={"address": "x"})
        self.assertEqual(r.status_code, 401)

    def test_tra_ve_dia_chi_day_du(self):
        r = client.post("/api/address",
                        json={"address": "659, CMT8, P. Hòa hưng, Tphcm"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json()["address"],
            "659, Cách Mạng Tháng Tám, Phường Hòa Hưng, "
            "Thành phố Hồ Chí Minh",
        )
        self.assertEqual(r.json()["warnings"], [])

    def test_tra_ve_loi_nhac_khi_phuong_khong_con(self):
        r = client.post("/api/address",
                        json={"address": "12 Lê Lợi, P. Bến Nghé, TP.HCM"})
        self.assertTrue(r.json()["warnings"])

    def test_khong_nhan_truong_la(self):
        r = client.post("/api/address", json={"address": "x", "them": 1})
        self.assertEqual(r.status_code, 422)

    def test_chuoi_qua_dai_thi_tu_choi(self):
        r = client.post("/api/address", json={"address": "x" * 3000})
        self.assertEqual(r.status_code, 422)


if __name__ == "__main__":
    unittest.main()
