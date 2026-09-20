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
            sheets, "_doc_o",
            return_value=("NHAN_SU", O_MAU if o is None else o)
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
            sheets, "_doc_o", return_value=("NHAN_SU", O_MAU)
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


KHOA_THAT_GIONG = json.dumps({
    "type": "service_account",
    "project_id": "du-an-thu",
    "private_key_id": "46994d7b0000000000000000000000000000abcd",
    "client_email": "hop-dong@du-an-thu.iam.gserviceaccount.com",
    "private_key": "-----BEGIN PRIVATE KEY-----\n"
                   + "A" * 1600 + "\n-----END PRIVATE KEY-----\n",
})


class SoiKhoa(unittest.TestCase):
    """Phân biệt được từng kiểu hỏng của phần private_key."""

    def test_khoa_nguyen_ven_thi_dat(self):
        soi = sheets.soi_khoa(json.loads(KHOA_THAT_GIONG))
        self.assertTrue(soi["ok"])
        self.assertEqual(soi["key_id_prefix"], "46994d7b")

    def test_thieu_han_private_key(self):
        soi = sheets.soi_khoa({"client_email": "a@b.iam.gserviceaccount.com"})
        self.assertFalse(soi["ok"])
        self.assertIn("private_key", soi["problem"])

    def test_mat_khoi_pem(self):
        soi = sheets.soi_khoa({"private_key": "A" * 2000})
        self.assertFalse(soi["ok"])
        self.assertIn("BEGIN PRIVATE KEY", soi["problem"])

    def test_xuong_dong_bi_bien_thanh_hai_ky_tu(self):
        khoa = ("-----BEGIN PRIVATE KEY-----\\n" + "A" * 1600
                + "\\n-----END PRIVATE KEY-----")
        soi = sheets.soi_khoa({"private_key": khoa})
        self.assertFalse(soi["ok"])
        self.assertIn("xuống dòng", soi["problem"])

    def test_khoa_bi_cat_ngan(self):
        khoa = "-----BEGIN PRIVATE KEY-----\nAAAA\n-----END PRIVATE KEY-----"
        soi = sheets.soi_khoa({"private_key": khoa})
        self.assertFalse(soi["ok"])
        self.assertIn("ngắn", soi["problem"])

    def test_khoa_hong_thi_khong_goi_google(self):
        """Khóa hỏng phải báo ngay, không mất 20 giây chờ mạng."""
        hong = json.dumps({"type": "service_account", "private_key": "xxx"})
        with dat_cau_hinh(ECONTRACT_GOOGLE_KEY=hong):
            sheets.xoa_bo_nho()
            with self.assertRaises(sheets.LoiSheet):
                sheets._lay_ve()

    def test_soi_khoa_khong_tra_ve_noi_dung_khoa(self):
        soi = sheets.soi_khoa(json.loads(KHOA_THAT_GIONG))
        self.assertNotIn("AAAA", json.dumps(soi))


class GiaiThichLoi(unittest.TestCase):
    """Mỗi nguyên nhân hỏng có một câu hướng dẫn riêng, làm theo được."""

    def test_khoa_bi_thu_hoi(self):
        cau = sheets._giai_thich_loi_ve(
            RuntimeError('{"error": "invalid_grant"}'))
        self.assertIn("thu hồi", cau)

    def test_chua_bat_api(self):
        cau = sheets._giai_thich_loi_ve(
            RuntimeError("Google Sheets API has not been used in project"))
        self.assertIn("Enable", cau)

    def test_khoa_hong_noi_dung(self):
        cau = sheets._giai_thich_loi_ve(
            ValueError("Could not deserialize key data"))
        self.assertIn("dán lại", cau.lower())

    def test_loi_la_van_kem_nguyen_van_de_do(self):
        cau = sheets._giai_thich_loi_ve(RuntimeError("chuyện lạ chưa gặp"))
        self.assertIn("chuyện lạ chưa gặp", cau)


class ChanDoan(unittest.TestCase):

    def test_hien_du_thong_tin_doi_chieu(self):
        with dat_cau_hinh(ECONTRACT_GOOGLE_KEY=KHOA_THAT_GIONG,
                          ECONTRACT_SHEET_ID="abc123"):
            ket_qua = sheets.chan_doan()
        self.assertEqual(ket_qua["key_id_prefix"], "46994d7b")
        self.assertEqual(ket_qua["project"], "du-an-thu")
        self.assertEqual(ket_qua["sheet_id"], "abc123")
        self.assertTrue(ket_qua["key_looks_valid"])

    def test_khong_lo_noi_dung_khoa(self):
        with dat_cau_hinh(ECONTRACT_GOOGLE_KEY=KHOA_THAT_GIONG,
                          ECONTRACT_SHEET_ID="abc123"):
            van_ban = json.dumps(sheets.chan_doan())
        self.assertNotIn("PRIVATE KEY", van_ban)
        self.assertNotIn("AAAA", van_ban)


class BaTramLeBa(unittest.TestCase):
    """403 có hai nguyên nhân khác hẳn nhau, phải chỉ đúng nguyên nhân."""

    def _goi_voi(self, van_ban: str):
        phan_hoi = mock.Mock(status_code=403, text=van_ban)
        with dat_cau_hinh(), mock.patch.object(
            sheets, "_lay_ve", return_value="ve"
        ), mock.patch("httpx.get", return_value=phan_hoi):
            with self.assertRaises(sheets.LoiSheet) as bat:
                sheets._goi("")
        return str(bat.exception)

    def test_chua_bat_api(self):
        self.assertIn("Enable", self._goi_voi(
            '{"status": "SERVICE_DISABLED"}'))

    def test_chua_chia_se_sheet(self):
        self.assertIn("Chia sẻ", self._goi_voi(
            '{"status": "PERMISSION_DENIED"}'))


class ThuVienDayDu(unittest.TestCase):
    """Chốt rằng máy chủ có đủ thư viện để xin vé vào cửa của Google.

    Mọi bài khác đều thay tầng mạng bằng dữ liệu giả nên không phát hiện
    được thiếu thư viện. Bài này nhập thật lớp Request của google-auth —
    lớp đó nằm trong google.auth.transport.requests và báo ImportError nếu
    thiếu gói requests, đúng lỗi đã gặp trên máy chủ.
    """

    def test_co_du_thu_vien_de_xin_ve_vao_cua(self):
        from google.auth.transport.requests import Request
        self.assertIsNotNone(Request())

    def test_requests_co_trong_danh_sach_thu_vien(self):
        import pathlib
        danh_sach = (pathlib.Path(__file__).resolve().parents[1]
                     / "requirements.txt").read_text()
        self.assertRegex(danh_sach, r"(?m)^requests==")

    def test_thieu_thu_vien_thi_noi_ro_la_loi_may_chu(self):
        cau = sheets._giai_thich_loi_ve(
            ImportError("The requests library is not installed."))
        self.assertIn("máy chủ", cau)
        self.assertIn("requirements.txt", cau)


# Đúng danh sách tab của Sheet nhân sự đang dùng thật, để bài kiểm thử bám
# vào tình huống có thật chứ không phải ví dụ tự nghĩ ra.
TAB_THAT = [
    "HUONG_DAN_SU_DUNG", "THONG_BAO", "TOKEN_THIET_BI", "NHAN_SU",
    "NHAT_KY_2026", "CHAM_CONG", "LUONG", "LICH_SU_LUONG", "DON_VI",
    "PHEP_NAM", "TAI_KHOAN", "DON_XIN_NGHI", "LOAI_NGHI", "CAU_HINH",
    "NHAT_KY_HE_THONG",
]


class ChonTab(unittest.TestCase):
    """Sheet dùng chung có cả chục tab, tab đầu là hướng dẫn chứ không phải
    dữ liệu, nên không được cứ nhắm mắt lấy tab đầu tiên."""

    def test_chon_nhan_su_chu_khong_phai_tab_dau(self):
        self.assertEqual(sheets.chon_tab(TAB_THAT), "NHAN_SU")

    def test_nhan_ra_nhieu_kieu_dat_ten(self):
        for ten in ("Nhân sự", "NHAN_VIEN", "Danh sách nhân viên",
                    "Employees", "STAFF"):
            self.assertEqual(sheets.chon_tab(["Hướng dẫn", ten]), ten)

    def test_ten_trung_khit_thang_ten_chi_chua_tu_khoa(self):
        self.assertEqual(
            sheets.chon_tab(["LICH_SU_NHAN_SU", "NHAN_SU"]), "NHAN_SU")

    def test_khong_tab_nao_khop_thi_lay_tab_dau(self):
        self.assertEqual(sheets.chon_tab(["Sheet1", "Sheet2"]), "Sheet1")

    def test_sheet_khong_co_tab_nao(self):
        with self.assertRaises(sheets.LoiSheet):
            sheets.chon_tab([])

    def test_khai_ten_tab_thi_theo_dung_ten_do(self):
        """Khai ECONTRACT_SHEET_TAB là quyết định cuối cùng, không đoán nữa."""
        with dat_cau_hinh(ECONTRACT_SHEET_TAB="LUONG"), mock.patch.object(
            sheets, "danh_sach_tab", return_value=TAB_THAT
        ) as gia:
            self.assertEqual(sheets._tab_dang_dung(), "LUONG")
        gia.assert_not_called()

    def test_khong_khai_thi_tu_tim(self):
        with dat_cau_hinh(), mock.patch.object(
            sheets, "danh_sach_tab", return_value=TAB_THAT
        ):
            self.assertEqual(sheets._tab_dang_dung(), "NHAN_SU")


class LoiThieuCotHoTen(unittest.TestCase):
    """Báo lỗi phải đủ thông tin để biết ngay phải sửa gì."""

    def setUp(self):
        sheets.xoa_bo_nho()

    def _loi(self):
        o = [["Mã", "Ghi chú"], ["NV-001", "x"]]
        with dat_cau_hinh(), mock.patch.object(
            sheets, "_doc_o", return_value=("CHAM_CONG", o)
        ):
            with self.assertRaises(sheets.LoiSheet) as bat:
                sheets.danh_sach_nhan_vien(lam_moi=True)
        return str(bat.exception)

    def test_noi_ro_dang_doc_tab_nao(self):
        self.assertIn("CHAM_CONG", self._loi())

    def test_liet_ke_cac_cot_thay_duoc(self):
        loi = self._loi()
        self.assertIn("Mã", loi)
        self.assertIn("Ghi chú", loi)

    def test_chi_cach_khai_ten_tab(self):
        self.assertIn("ECONTRACT_SHEET_TAB", self._loi())


if __name__ == "__main__":
    unittest.main()
