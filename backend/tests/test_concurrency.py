"""Kiểm thử hàng đợi dựng PDF.

Mỗi lượt dựng chiếm khoảng 300 MB vì LibreOffice. Chạy song song trên máy
chủ 512 MB sẽ hết bộ nhớ, nên mặc định chỉ cho một lượt chạy một lúc.
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest import mock

from app.services import documents


class TestGioiHanSongSong(unittest.TestCase):
    def test_mac_dinh_la_mot(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ECONTRACT_MAX_PDF_SONG_SONG", None)
            self.assertEqual(documents._max_song_song(), 1)

    def test_doc_duoc_tu_bien_moi_truong(self):
        with mock.patch.dict(os.environ, {"ECONTRACT_MAX_PDF_SONG_SONG": "3"}):
            self.assertEqual(documents._max_song_song(), 3)

    def test_gia_tri_hong_thi_ve_mot(self):
        for gia_tri in ("khong-phai-so", "", "0", "-5"):
            with self.subTest(gia_tri=gia_tri):
                with mock.patch.dict(
                    os.environ, {"ECONTRACT_MAX_PDF_SONG_SONG": gia_tri}
                ):
                    self.assertEqual(documents._max_song_song(), 1)

    def test_bao_ban_khi_het_luot(self):
        """Đầy hàng đợi thì báo bận, không treo và không tràn bộ nhớ."""
        self.assertTrue(documents._cong_pdf.acquire(timeout=5))
        try:
            with mock.patch.object(documents, "THOI_GIAN_CHO_LUOT", 0.1):
                with self.assertRaises(RuntimeError) as bat:
                    documents.build_pdf("victoria", {}, Path("/tmp/khong-dung.pdf"))
            self.assertIn("bận", str(bat.exception))
        finally:
            documents._cong_pdf.release()

    def test_tra_lai_luot_sau_khi_loi(self):
        """Hồ sơ hỏng không được làm kẹt hàng đợi vĩnh viễn."""
        with self.assertRaises(Exception):
            documents.build_pdf("victoria", {}, Path("/tmp/khong-dung.pdf"))
        # Nếu cổng không được trả lại thì lần lấy sau sẽ thất bại.
        self.assertTrue(documents._cong_pdf.acquire(timeout=5))
        documents._cong_pdf.release()


if __name__ == "__main__":
    unittest.main()
