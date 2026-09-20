"""Kiểm thử hợp đồng thử việc.

Thử việc khác hẳn hợp đồng chính thức: một tờ, không phụ lục lương, không
thỏa thuận trách nhiệm, và không khấu trừ bảo hiểm hay công đoàn.
"""
from __future__ import annotations

import shutil
import unittest
from copy import deepcopy

from tests import logged_in_client

client = logged_in_client()


def ho_so() -> dict:
    return {
        "unit_id": "gau_panda",
        "employee": {
            "full_name": "Nguyễn Thị Minh An",
            "code": "HTV010",
            "birth_date": "1999-01-01",
            "gender": "Nữ",
            "nationality": "Việt Nam",
            "hometown": "Bạc Liêu",
            "identity_number": "079199000123",
            "identity_issue_date": "2025-01-01",
            "identity_issuer": "Cục Cảnh sát",
            "permanent_address": "12 Lê Lợi, Quận 1, Thành phố Hồ Chí Minh",
        },
        "job": {
            "position_id": "preschool_teacher",
            "department": "Giáo viên",
            "supervisor_name": "Trần Thị Mỹ Lan",
        },
        "signing_date": "2026-08-01",
        "probation": {
            "start_date": "2026-08-01",
            "end_date": "2026-09-30",
            "full_gross": "8800000",
            "rate_percent": "85",
            "work_hours": "07g00 – 17g00",
            "rest_hours": "12g00 – 14g00",
        },
        "payment": {"window_text": "Từ ngày 01 – ngày 05 hàng tháng"},
    }


class TestDuLieuVao(unittest.TestCase):
    """Hình thức dữ liệu; không dựng PDF nên chạy nhanh."""

    def _gui(self, sua=None):
        d = ho_so()
        if sua:
            sua(d)
        return client.post("/api/generate/probation", json=d)

    def test_thieu_que_quan_thi_tu_choi(self):
        """Mẫu có dòng Quê quán nên không được để trống rồi in ra."""
        r = self._gui(lambda d: d["employee"].pop("hometown"))
        self.assertEqual(r.status_code, 422)

    def test_thieu_nguoi_dieu_hanh_thi_tu_choi(self):
        r = self._gui(lambda d: d["job"].pop("supervisor_name"))
        self.assertEqual(r.status_code, 422)

    def test_khong_nhan_them_truong_la(self):
        r = self._gui(lambda d: d.update(compensation={"salary_mode": "gross"}))
        self.assertEqual(r.status_code, 422)

    def test_luong_bang_khong_thi_tu_choi(self):
        r = self._gui(lambda d: d["probation"].update(full_gross="0"))
        self.assertEqual(r.status_code, 422)

    def test_ty_le_vuot_100_thi_tu_choi(self):
        r = self._gui(lambda d: d["probation"].update(rate_percent="150"))
        self.assertEqual(r.status_code, 400)

    def test_ngay_ket_thuc_truoc_ngay_bat_dau(self):
        r = self._gui(lambda d: d["probation"].update(end_date="2026-07-01"))
        self.assertEqual(r.status_code, 400)

    def test_co_so_khong_duoc_phep_thi_bi_chan(self):
        r = self._gui(lambda d: d.update(unit_id="khong_co_that"))
        self.assertIn(r.status_code, (400, 403))


@unittest.skipUnless(shutil.which("soffice"), "Cần LibreOffice mới dựng được PDF")
class TestPdfThuViec(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.phan_hoi = client.post("/api/generate/probation", json=ho_so())

    def test_tao_duoc_pdf(self):
        self.assertEqual(self.phan_hoi.status_code, 200)
        self.assertEqual(self.phan_hoi.headers["content-type"], "application/pdf")

    def test_ten_file_kem_ma_nhan_vien(self):
        self.assertIn("HTV010", self.phan_hoi.headers["content-disposition"])

    def test_so_hop_dong_theo_ma_nhan_vien(self):
        self.assertEqual(self.phan_hoi.headers["X-Contract-Number"],
                         "GPD_HDTV_HTV010")

    def _chu(self) -> str:
        import io

        from pypdf import PdfReader

        doc = PdfReader(io.BytesIO(self.phan_hoi.content))
        return "\n".join((t.extract_text() or "") for t in doc.pages)

    def test_tinh_dung_85_phan_tram(self):
        chu = self._chu()
        self.assertIn("8.800.000", chu)
        self.assertIn("7.480.000", chu)

    def test_khong_kem_phu_luc_va_thoa_thuan(self):
        chu = self._chu()
        self.assertNotIn("PHỤ LỤC", chu.upper())
        self.assertNotIn("THỎA THUẬN TRÁCH NHIỆM", chu.upper())
        self.assertIn("HỢP ĐỒNG THỬ VIỆC", chu.upper())

    def test_khong_co_bang_khau_tru(self):
        """Thử việc chưa hưởng chế độ nên không được in dòng khấu trừ nào."""
        chu = self._chu()
        for cam in ("Bảo hiểm", "Đoàn phí", "Công đoàn", "Thực nhận"):
            self.assertNotIn(cam, chu, cam)

    def test_dien_dung_thong_tin_nguoi_lao_dong(self):
        chu = self._chu()
        for mong_doi in ("Nguyễn Thị Minh An", "Bạc Liêu", "01/01/1999",
                         "Trần Thị Mỹ Lan", "Cục Cảnh sát"):
            self.assertIn(mong_doi, chu, mong_doi)

    def test_khong_con_bien_chua_thay(self):
        self.assertNotIn("{{", self._chu())

    def test_dung_phap_nhan_cua_co_so(self):
        self.assertIn("IBRIGHT", self._chu())


class TestThoiHan(unittest.TestCase):
    """Số tháng tự tính từ hai mốc ngày."""

    def _thang(self, bat_dau: str, ket_thuc: str) -> str:
        import sys

        sys.path.insert(0, str(__import__("app.config", fromlist=["x"]).KIT_DIR))
        from generate_demo import build_probation_context

        d = deepcopy(ho_so())
        d["probation"].update(start_date=bat_dau, end_date=ket_thuc)
        d.pop("unit_id")
        ctx, _ = build_probation_context("gau_panda", d)
        return ctx["probation"]["term_text"]

    def test_hai_thang_tron(self):
        self.assertEqual(self._thang("2026-08-01", "2026-09-30"), "2 tháng")

    def test_mot_thang_tron(self):
        self.assertEqual(self._thang("2026-08-01", "2026-08-31"), "1 tháng")

    def test_thang_hai_ngan_ngay_van_tron(self):
        self.assertEqual(self._thang("2026-02-01", "2026-02-28"), "1 tháng")


if __name__ == "__main__":
    unittest.main()
