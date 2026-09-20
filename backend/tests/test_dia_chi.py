"""Kiểm thử viết đầy đủ địa chỉ.

Nguyên tắc: chỉ mở rộng chữ viết tắt và sửa cách viết hoa. Không thêm
thông tin người dùng chưa gõ, không bỏ bớt phần nào, và không đổi tên
phường xã theo đợt sáp nhập.
"""
from __future__ import annotations

import unittest

from app.services.dia_chi import viet_day_du
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
            "Số 5, Khu phố 3, Thị trấn Củ Chi, Thành phố Hồ Chí Minh",
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

    def test_sua_cach_viet_hoa(self):
        self.assertEqual(viet_day_du("32/11 đường 13A, bình hưng hòa, HCM"),
                         "32/11 Đường 13A, Bình Hưng Hòa, "
                         "Thành phố Hồ Chí Minh")

    def test_tu_so_khong_viet_hoa_giua_doan(self):
        self.assertEqual(viet_day_du("1/4 Đường số 33, Phường An Khánh"),
                         "1/4 Đường số 33, Phường An Khánh")

    def test_dia_chi_da_day_du_thi_giu_nguyen(self):
        day_du = ("946/6 Tân Kỳ Tân Quý, Phường Bình Hưng Hoà, "
                  "Thành phố Hồ Chí Minh")
        self.assertEqual(viet_day_du(day_du), day_du)

    def test_khong_tu_doi_ten_phuong_theo_sap_nhap(self):
        """Đoán sai tên phường trong hợp đồng còn tệ hơn để nguyên."""
        ra = viet_day_du("P. Hòa Hưng, Quận 10, TPHCM")
        self.assertIn("Phường Hòa Hưng", ra)
        self.assertIn("Quận 10", ra)

    def test_khong_bo_bot_phan_nao(self):
        ra = viet_day_du("659, CMT8, P. Hòa hưng, Tphcm")
        self.assertEqual(ra.count(","), 3)

    def test_o_trong_thi_tra_ve_trong(self):
        for xau in ("", "   ", None):
            self.assertEqual(viet_day_du(xau), "")

    def test_chu_la_thi_giu_nguyen_chu_khong_bia(self):
        self.assertEqual(viet_day_du("Ấp Bảy Ngàn, Hậu Giang"),
                         "Ấp Bảy Ngàn, Hậu Giang")

    def test_thua_dau_phay_va_khoang_trang(self):
        self.assertEqual(viet_day_du("  12  Lê Lợi ,, Q.1 ,  "),
                         "12 Lê Lợi, Quận 1")


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

    def test_khong_nhan_truong_la(self):
        r = client.post("/api/address", json={"address": "x", "them": 1})
        self.assertEqual(r.status_code, 422)

    def test_chuoi_qua_dai_thi_tu_choi(self):
        r = client.post("/api/address", json={"address": "x" * 3000})
        self.assertEqual(r.status_code, 422)


if __name__ == "__main__":
    unittest.main()
