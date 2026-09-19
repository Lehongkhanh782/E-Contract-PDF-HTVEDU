# E-Contract-PDF-HTVEDU

Ứng dụng tạo hợp đồng lao động, phụ lục lương và thỏa thuận trách nhiệm
cho 4 đơn vị: Vườn Sáng Tạo, Victoria, Gấu Panda, Đại Dương Xanh.

## Tình trạng hiện tại

Repo đang ở **giai đoạn 1**: mới có phần lõi thử nghiệm (JSON → Word → PDF).
Chưa có website, đăng nhập, database, OCR hay chức năng phát hành chính thức.

Mọi PDF do chương trình tạo ra đều mang dòng
`BẢN THỬ NGHIỆM DỮ LIỆU GIẢ CHƯA DÙNG KÝ` và **không dùng để ký thật**.

## Nội dung repo

| Thư mục | Nội dung |
| --- | --- |
| `contract_kit/` | Phần lõi thử nghiệm: mẫu Word, cấu hình 4 đơn vị, bộ tính lương |
| `docs/` | Bản kế hoạch/đặc tả đầy đủ của ứng dụng |

Chi tiết từng file xem `contract_kit/README.md`.
Bản đồ 51 biến và các điểm cần chốt xem `contract_kit/Ban_do_truong_va_cac_diem_can_chot.md`.

## Yêu cầu môi trường

- Python 3.11 trở lên
- LibreOffice **kèm gói Writer** (`libreoffice-writer`) — thiếu gói này sẽ
  báo lỗi `Không chuyển được Word sang PDF`
- Font hỗ trợ tiếng Việt, nên cài đúng các font mà mẫu Word đang dùng

## Cách chạy thử

```bash
# 1. Tạo môi trường ảo và cài thư viện
python3 -m venv .venv
.venv/bin/pip install -r contract_kit/requirements.txt

# 2. Chạy kiểm thử (19 bài)
cd contract_kit && ../.venv/bin/python -m unittest test_core.py

# 3. Chỉ xem phép tính, không tạo file
../.venv/bin/python generate_demo.py --calculate-only

# 4. Tạo PDF thử nghiệm
../.venv/bin/python generate_demo.py --unit dai_duong_xanh --output out/Bo_hop_dong_thu.pdf
```

Chọn đơn vị bằng một trong các giá trị `vuon_sang_tao`, `victoria`,
`gau_panda`, `dai_duong_xanh`.

Thử chiều tính ngược từ Net, thêm `--input examples/employee_net_demo.json`.

## Nguyên tắc về dữ liệu

File thật của nhân viên và hợp đồng đã phát hành **không được đưa vào Git**.
Repo chỉ chứa mẫu đã được phép dùng, dữ liệu giả để kiểm thử và mã nguồn.
Các biến bí mật lưu ngoài code.

## Bước tiếp theo

Xem mục 18 (lộ trình) và mục 22 (những thông tin còn cần chốt) trong
`docs/Ke_hoach_ung_dung_hop_dong_4_co_so.md`.
