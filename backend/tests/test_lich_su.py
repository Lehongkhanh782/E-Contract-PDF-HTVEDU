"""Kiểm thử ghi và đọc lịch sử hợp đồng.

Không gọi Google thật. Điều quan trọng nhất ở đây: Sheet trục trặc thì
mất dòng lịch sử, chứ không được mất luôn cái PDF vừa dựng xong.
"""
from __future__ import annotations

import shutil
import unittest
from unittest import mock

from app.services import sheets
from tests import logged_in_client, sample_request
from tests.test_thu_viec import ho_so

client = logged_in_client()

CAN_LIBREOFFICE = unittest.skipUnless(
    shutil.which("soffice"), "Cần LibreOffice mới dựng được PDF"
)

LICH_SU_MAU = {
    "HTV010": [{
        "created_at": "21/09/2026 10:30",
        "code": "HTV010",
        "full_name": "Nguyễn Thị Minh An",
        "unit_id": "gau_panda",
        "contract_type": "Hợp đồng thử việc",
        "contract_number": "GPD/HDTV/HTV010",
        "signing_date": "21/09/2026",
        "created_by": "Chị Lan",
    }]
}


class TestDocLichSuQuaApi(unittest.TestCase):
    def test_tra_ve_lich_su_da_ghi(self):
        with mock.patch.object(sheets, "lich_su_theo_ma",
                               return_value=LICH_SU_MAU):
            r = client.get("/api/history")
        self.assertEqual(r.status_code, 200)
        than = r.json()
        self.assertTrue(than["available"])
        self.assertEqual(than["history"]["HTV010"][0]["contract_number"],
                         "GPD/HDTV/HTV010")

    def test_chua_noi_sheet_thi_rong_chu_khong_loi(self):
        """Chưa nối Sheet không được làm hỏng hộp chọn nhân viên."""
        with mock.patch.object(sheets, "lich_su_theo_ma",
                               side_effect=sheets.ChuaCauHinh("chưa khai")):
            r = client.get("/api/history")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["available"])
        self.assertEqual(r.json()["history"], {})

    def test_sheet_loi_thi_kem_ly_do(self):
        with mock.patch.object(sheets, "lich_su_theo_ma",
                               side_effect=sheets.LoiSheet("Google từ chối")):
            r = client.get("/api/history")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Google từ chối", r.json()["note"])

    def test_loi_la_cung_khong_do(self):
        with mock.patch.object(sheets, "lich_su_theo_ma",
                               side_effect=ZeroDivisionError("lạ")):
            r = client.get("/api/history")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["available"])

    def test_chua_dang_nhap_thi_chan(self):
        from fastapi.testclient import TestClient

        from app.main import app

        r = TestClient(app).get("/api/history")
        self.assertEqual(r.status_code, 401)


@CAN_LIBREOFFICE
class TestGhiKhiTaoHopDong(unittest.TestCase):
    """Tạo PDF xong phải ghi đúng một dòng lịch sử."""

    def test_ghi_dung_thong_tin_nguoi_vua_lam_hop_dong(self):
        with mock.patch.object(sheets, "ghi_lich_su") as ghi:
            r = client.post("/api/generate/probation", json=ho_so())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["X-History-Saved"], "true")
        ghi.assert_called_once()
        ban_ghi = ghi.call_args.args[0]
        self.assertEqual(ban_ghi["code"], "HTV010")
        self.assertEqual(ban_ghi["full_name"], "Nguyễn Thị Minh An")
        self.assertEqual(ban_ghi["unit_id"], "gau_panda")
        self.assertEqual(ban_ghi["contract_type"], "probation")
        self.assertEqual(ban_ghi["contract_number"], "GPD/HDTV/HTV010")
        # Ngày ký ghi theo cách người Việt đọc, không phải 2026-08-01.
        self.assertEqual(ban_ghi["signing_date"], "01/08/2026")
        self.assertTrue(ban_ghi["created_by"])

    def test_sheet_hong_van_tai_duoc_pdf(self):
        """Điều quan trọng nhất: không được mất hợp đồng vì Sheet trục trặc."""
        with mock.patch.object(sheets, "ghi_lich_su",
                               side_effect=sheets.LoiSheet("Google từ chối")):
            r = client.post("/api/generate/probation", json=ho_so())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["content-type"], "application/pdf")
        self.assertGreater(len(r.content), 1000)
        # Giao diện đọc header này để nhắc người dùng kiểm tra quyền Sheet.
        self.assertEqual(r.headers["X-History-Saved"], "false")

    def test_loi_la_khi_ghi_cung_khong_mat_pdf(self):
        with mock.patch.object(sheets, "ghi_lich_su",
                               side_effect=ZeroDivisionError("lạ")):
            r = client.post("/api/generate/probation", json=ho_so())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["X-History-Saved"], "false")

    def test_hop_dong_chinh_thuc_cung_ghi_lich_su(self):
        """Không chỉ thử việc: hợp đồng lao động cũng phải để lại dấu vết."""
        ho = sample_request("dai_duong_xanh")
        with mock.patch.object(sheets, "ghi_lich_su") as ghi:
            r = client.post("/api/generate", json=ho)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["X-History-Saved"], "true")
        ban_ghi = ghi.call_args.args[0]
        self.assertEqual(ban_ghi["contract_type"], "official")
        self.assertEqual(ban_ghi["unit_id"], "dai_duong_xanh")
        self.assertIn("HDLD", ban_ghi["contract_number"])

    def test_ho_so_sai_thi_khong_ghi_lich_su(self):
        """Hợp đồng không dựng được thì không được để lại dấu vết là đã cấp."""
        sai = ho_so()
        sai["probation"]["rate_percent"] = "150"
        with mock.patch.object(sheets, "ghi_lich_su") as ghi:
            r = client.post("/api/generate/probation", json=sai)
        self.assertEqual(r.status_code, 400)
        ghi.assert_not_called()


if __name__ == "__main__":
    unittest.main()
