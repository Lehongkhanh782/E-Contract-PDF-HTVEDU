"""Kiểm thử đọc Google Sheet.

Không gọi Google thật: mọi bài đều thay tầng mạng bằng dữ liệu giả, nên
chạy được trên máy không có khóa và không phụ thuộc mạng.
"""
from __future__ import annotations

import json
import os
import unittest
from unittest import mock

from app.services import sheets
from tests import logged_in_client

client = logged_in_client()

KHOA_GIA = json.dumps({
    "type": "service_account",
    "client_email": "hop-dong@du-an-thu.iam.gserviceaccount.com",
    "private_key": "-----BEGIN PRIVATE KEY-----\nGIA\n-----END PRIVATE KEY-----\n",
})

O_MAU = [
    ["Mã nhân viên", "Họ và tên", "Ngày sinh", "Giới tính", "Số CCCD",
     "Ngày cấp", "Nơi cấp", "Nơi thường trú", "Chức vụ", "Ghi chú"],
    ["NV-001", "Nguyễn Thị Minh An", "01/01/1999", "Nữ", "079199000123",
     "01/01/2025", "Cục Cảnh sát", "12 Lê Lợi, Quận 1, TP.HCM",
     "Giáo viên Tiếng Anh", "đang làm"],
    ["NV-002", "Trần Văn Bốn", "05/05/1990", "Nam", "079090000456",
     "02/02/2022", "Cục Cảnh sát", "34 Hai Bà Trưng, Quận 3, TP.HCM",
     "Bảo mẫu", ""],
    ["", "", "", "", "", "", "", "", "", ""],
]


def dat_cau_hinh(**them):
    moi = {"ECONTRACT_GOOGLE_KEY": KHOA_GIA, "ECONTRACT_SHEET_ID": "abc123"}
    moi.update(them)
    return mock.patch.dict(os.environ, moi)


class TestCauHinh(unittest.TestCase):
    def setUp(self):
        sheets.xoa_bo_nho()

    def test_chua_khai_thi_tat_chuc_nang(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ECONTRACT_GOOGLE_KEY", None)
            os.environ.pop("ECONTRACT_SHEET_ID", None)
            self.assertFalse(sheets.da_cau_hinh())

    def test_khai_du_thi_bat(self):
        with dat_cau_hinh():
            self.assertTrue(sheets.da_cau_hinh())
            self.assertEqual(
                sheets.email_tai_khoan_may(),
                "hop-dong@du-an-thu.iam.gserviceaccount.com",
            )

    def test_khoa_khong_phai_json_bao_loi_ro_rang(self):
        with dat_cau_hinh(ECONTRACT_GOOGLE_KEY="day khong phai json"):
            with self.assertRaises(sheets.ChuaCauHinh) as bat:
                sheets._cau_hinh()
            self.assertIn("JSON", str(bat.exception))

    def test_khoa_sai_loai_bao_loi_ro_rang(self):
        khac = json.dumps({"type": "authorized_user", "client_email": "x@y.z"})
        with dat_cau_hinh(ECONTRACT_GOOGLE_KEY=khac):
            with self.assertRaises(sheets.ChuaCauHinh) as bat:
                sheets._cau_hinh()
            self.assertIn("tài khoản máy", str(bat.exception))

    def test_dan_ca_duong_lien_ket_van_lay_duoc_ma(self):
        lien_ket = "https://docs.google.com/spreadsheets/d/1AbC_deF-123456789xyz/edit#gid=0"
        with dat_cau_hinh(ECONTRACT_SHEET_ID=lien_ket):
            _, ma, _ = sheets._cau_hinh()
            self.assertEqual(ma, "1AbC_deF-123456789xyz")


class TestDoanCot(unittest.TestCase):
    def test_nhan_ra_cac_cot_thuong_gap(self):
        cot = sheets.doan_cot(O_MAU[0])
        self.assertEqual(cot["code"], 0)
        self.assertEqual(cot["full_name"], 1)
        self.assertEqual(cot["identity_number"], 4)
        self.assertEqual(cot["permanent_address"], 7)

    def test_ngay_cap_khong_bi_nham_sang_ngay_sinh(self):
        cot = sheets.doan_cot(O_MAU[0])
        self.assertEqual(cot["birth_date"], 2)
        self.assertEqual(cot["identity_issue_date"], 5)

    def test_bo_qua_cot_khong_hieu(self):
        cot = sheets.doan_cot(O_MAU[0])
        self.assertNotIn(9, cot.values())

    def test_tieu_de_tieng_anh_cung_nhan_ra(self):
        cot = sheets.doan_cot(["Employee code", "Full name", "Date of birth"])
        self.assertEqual(cot["code"], 0)
        self.assertEqual(cot["full_name"], 1)
        self.assertEqual(cot["birth_date"], 2)

    def test_khong_co_cot_nao_khop_thi_tra_rong(self):
        self.assertEqual(sheets.doan_cot(["aaa", "bbb"]), {})


class TestDocNhanVien(unittest.TestCase):
    def setUp(self):
        sheets.xoa_bo_nho()

    def chay(self, o=None, **them):
        with dat_cau_hinh(**them), mock.patch.object(
            sheets, "_doc_o", return_value=O_MAU if o is None else o
        ):
            return sheets.danh_sach_nhan_vien(lam_moi=True)

    def test_doc_dung_so_nhan_vien(self):
        ket_qua = self.chay()
        self.assertEqual(len(ket_qua["employees"]), 2)

    def test_bo_qua_dong_trong(self):
        """Sheet hay có dòng trống ở cuối; không được thành nhân viên ma."""
        ten = [nv["full_name"] for nv in self.chay()["employees"]]
        self.assertEqual(ten, ["Nguyễn Thị Minh An", "Trần Văn Bốn"])

    def test_quy_ve_dung_ten_truong_cua_bieu_mau(self):
        dau = self.chay()["employees"][0]
        self.assertEqual(dau["code"], "NV-001")
        self.assertEqual(dau["identity_number"], "079199000123")
        self.assertEqual(dau["gender"], "Nữ")
        self.assertIn("Lê Lợi", dau["permanent_address"])

    def test_dong_thieu_o_cuoi_khong_gay_loi(self):
        thieu = [O_MAU[0], ["NV-003", "Lê Thị Năm"]]
        nv = self.chay(thieu)["employees"][0]
        self.assertEqual(nv["full_name"], "Lê Thị Năm")
        self.assertEqual(nv["permanent_address"], "")

    def test_thieu_cot_ho_ten_thi_bao_loi_ro_rang(self):
        with self.assertRaises(sheets.LoiSheet) as bat:
            self.chay([["Cột lạ", "Cột khác"], ["a", "b"]])
        self.assertIn("họ tên", str(bat.exception))

    def test_sheet_rong_bao_loi(self):
        with self.assertRaises(sheets.LoiSheet):
            self.chay([])

    def test_lan_hai_lay_tu_bo_nho_tam(self):
        with dat_cau_hinh(), mock.patch.object(
            sheets, "_doc_o", return_value=O_MAU
        ) as gia:
            sheets.danh_sach_nhan_vien(lam_moi=True)
            lai = sheets.danh_sach_nhan_vien()
            self.assertTrue(lai["cached"])
            self.assertEqual(gia.call_count, 1)


class TestApi(unittest.TestCase):
    def setUp(self):
        sheets.xoa_bo_nho()

    def test_chua_dang_nhap_thi_bi_chan(self):
        from fastapi.testclient import TestClient

        from app.main import app

        khach = TestClient(app)
        self.assertEqual(khach.get("/api/employees").status_code, 401)
        self.assertEqual(khach.get("/api/sheets/status").status_code, 401)

    def test_chua_cau_hinh_thi_status_bao_tat(self):
        with mock.patch.object(sheets, "da_cau_hinh", return_value=False):
            body = client.get("/api/sheets/status").json()
        self.assertFalse(body["configured"])

    def test_chua_cau_hinh_thi_employees_tra_503(self):
        with mock.patch.object(
            sheets, "danh_sach_nhan_vien",
            side_effect=sheets.ChuaCauHinh("chưa khai")
        ):
            self.assertEqual(client.get("/api/employees").status_code, 503)

    def test_loi_sheet_tra_502_kem_loi_giai_thich(self):
        with mock.patch.object(
            sheets, "danh_sach_nhan_vien",
            side_effect=sheets.LoiSheet("Google từ chối truy cập")
        ):
            phan_hoi = client.get("/api/employees")
        self.assertEqual(phan_hoi.status_code, 502)
        self.assertIn("từ chối", phan_hoi.json()["detail"])

    def test_loi_la_khong_thanh_500(self):
        with mock.patch.object(
            sheets, "danh_sach_nhan_vien", side_effect=ZeroDivisionError("lạ")
        ):
            phan_hoi = client.get("/api/employees")
        self.assertEqual(phan_hoi.status_code, 502)

    def test_tra_ve_danh_sach(self):
        gia = {"employees": [{"full_name": "Nguyễn Thị Minh An"}],
               "columns": {"full_name": 1}, "headers": [], "cached": False}
        with mock.patch.object(sheets, "danh_sach_nhan_vien", return_value=gia):
            body = client.get("/api/employees").json()
        self.assertEqual(len(body["employees"]), 1)

    def test_khong_bao_gio_lo_khoa_bi_mat(self):
        with dat_cau_hinh(), mock.patch.object(
            sheets, "danh_sach_tab", return_value=["Nhân sự"]
        ), mock.patch.object(
            sheets, "danh_sach_nhan_vien",
            side_effect=sheets.LoiSheet("hỏng")
        ):
            van_ban = client.get("/api/sheets/status").text
        self.assertNotIn("PRIVATE KEY", van_ban)
        self.assertNotIn("GIA", van_ban.replace("gserviceaccount", ""))


if __name__ == "__main__":
    unittest.main()
