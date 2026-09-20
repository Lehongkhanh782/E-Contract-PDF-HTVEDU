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
            # Huyện Trà Ôn bị bỏ vì cấp huyện không còn.
            "Xã Hòa Bình, Tỉnh Vĩnh Long",
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
        """Phần địa chỉ không phải đơn vị hành chính thì không đụng tới."""
        # Hậu Giang nay thuộc thành phố Cần Thơ theo Nghị quyết 60-NQ/TW.
        self.assertEqual(viet_day_du("Ấp Bảy Ngàn, Hậu Giang"),
                         "Ấp Bảy Ngàn, Thành phố Cần Thơ")
        self.assertEqual(viet_day_du("CC Sky Garden, Hẻm 12"),
                         "Chung cư Sky Garden, Hẻm 12")

    def test_chu_mo_rong_khong_bi_viet_hoa_lai(self):
        """"ql" ra "Quốc lộ" chứ không phải "Quốc Lộ"."""
        self.assertEqual(viet_day_du("QL 1A, X. Bình Mỹ, Vĩnh Long"),
                         "Quốc lộ 1A, Xã Bình Mỹ, Tỉnh Vĩnh Long")
        self.assertIn("Khu dân cư", viet_day_du("KDC Bình Hưng, HCM"))

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

    def test_kem_link_tra_cuu_khi_phuong_khong_con(self):
        """Nhân sự cần chỗ tra ngay, chứ không chỉ biết là sai."""
        ra = chuan_hoa("12 Lê Lợi, Phường Bến Nghé, Quận 1, TP.HCM")
        self.assertIn("vnexpress.net", ra["lookup_url"])

    def test_dia_chi_dung_thi_khong_kem_link(self):
        self.assertIsNone(chuan_hoa("P. Hòa Hưng, TPHCM")["lookup_url"])

    def test_bo_quan_huyen_thi_khong_kem_link(self):
        """Đây không phải lỗi của người nhập nên không cần tra."""
        ra = chuan_hoa("số 7, P. Củ Chi, huyện Củ Chi, tphcm")
        self.assertIsNone(ra["lookup_url"])

    def test_khong_nhan_ra_tinh_thi_nhac(self):
        ra = chuan_hoa("12 Lê Lợi, Phường Nào Đó")
        self.assertTrue(any("tỉnh thành" in n for n in ra["warnings"]))

    def test_dia_chi_dung_thi_khong_nhac_gi(self):
        for x in ("659, CMT8, P. Hòa hưng, Tphcm",
                  "17 Bùi Huy Bích, phường Phú Định, TPHCM",
                  "1/4 Đường số 33, P. An Khánh, TP HCM"):
            self.assertEqual(chuan_hoa(x)["warnings"], [], x)


class TestHopNhatTinh(unittest.TestCase):
    """Tỉnh cũ đã hợp nhất thì quy về tỉnh thành mới.

    Bảng hợp nhất lấy từ Nghị quyết 60-NQ/TW, phần phụ lục.
    """

    def test_binh_duong_nay_thuoc_thanh_pho_ho_chi_minh(self):
        ra = chuan_hoa("12 Lê Lợi, Phường Thủ Dầu Một, Bình Dương")
        self.assertIn("Thành phố Hồ Chí Minh", ra["address"])
        self.assertNotIn("Bình Dương", ra["address"])
        self.assertTrue(any("60-NQ/TW" in n for n in ra["warnings"]))

    def test_ba_ria_vung_tau_nay_thuoc_thanh_pho_ho_chi_minh(self):
        ra = chuan_hoa("ấp 3, Xã Long Điền, Bà Rịa - Vũng Tàu")
        self.assertIn("Thành phố Hồ Chí Minh", ra["address"])

    def test_tra_vinh_nay_thuoc_vinh_long(self):
        ra = chuan_hoa("số 9, Xã Cầu Kè, Trà Vinh")
        self.assertIn("Vĩnh Long", ra["address"])

    def test_tinh_khong_sap_nhap_thi_giu_nguyen(self):
        ra = chuan_hoa("12 Lê Lợi, Phường Đông Hà, Tỉnh Quảng Ninh")
        self.assertIn("Quảng Ninh", ra["address"])
        self.assertFalse(any("60-NQ/TW" in n for n in ra["warnings"]))

    def test_bo_ca_cap_thanh_pho_thuoc_tinh(self):
        """Thành phố thuộc tỉnh cũng là cấp huyện, cũng không còn."""
        ra = chuan_hoa("12 Lê Lợi, Phường Thủ Dầu Một, TP Thủ Dầu Một, "
                       "Bình Dương")
        self.assertNotIn("Thành phố Thủ Dầu Một", ra["address"])
        self.assertTrue(ra["address"].endswith("Thành phố Hồ Chí Minh"))

    def test_khong_xoa_nham_doan_ten_tinh_thanh(self):
        """Tên tỉnh cũng bắt đầu bằng "Thành phố" nên phải được giữ lại."""
        ra = chuan_hoa("659, P. Hòa Hưng, Thành phố Hồ Chí Minh")
        self.assertIn("Thành phố Hồ Chí Minh", ra["address"])

    def test_phuong_sai_gon_khong_bi_nham_thanh_ten_thanh_pho(self):
        """Sài Gòn vừa là tên gọi khác của thành phố, vừa là tên một phường."""
        ra = chuan_hoa("1 Lê Duẩn, P. Sài Gòn, TPHCM")
        self.assertEqual(ra["address"],
                         "1 Lê Duẩn, Phường Sài Gòn, Thành phố Hồ Chí Minh")
        self.assertEqual(ra["warnings"], [])


class TestFileHopNhatTinh(unittest.TestCase):
    """Chốt tính toàn vẹn của bảng hợp nhất trích từ nghị quyết."""

    def setUp(self):
        import json

        from app.config import CONFIG_DIR

        self.goc = json.loads(
            (CONFIG_DIR / "sap_nhap_tinh.json").read_text(encoding="utf-8")
        )

    def test_23_truong_hop_hop_nhat_va_11_tinh_giu_nguyen(self):
        self.assertEqual(self.goc["so_truong_hop_hop_nhat"], 23)
        self.assertEqual(len(self.goc["tinh_giu_nguyen"]), 11)
        self.assertEqual(
            self.goc["so_truong_hop_hop_nhat"] + len(self.goc["tinh_giu_nguyen"]),
            34,
        )

    def test_ghi_ro_nguon(self):
        self.assertIn("60-NQ/TW", self.goc["nguon"])

    def test_co_truong_hop_cua_nha_truong(self):
        m = self.goc["tinh_cu_sang_moi"]
        self.assertEqual(m["Bình Dương"], "Thành phố Hồ Chí Minh")
        self.assertEqual(m["Bà Rịa - Vũng Tàu"], "Thành phố Hồ Chí Minh")


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
