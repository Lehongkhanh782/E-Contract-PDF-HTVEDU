# E-Contract-PDF-HTVEDU

Ứng dụng tạo hợp đồng lao động, phụ lục lương và thỏa thuận trách nhiệm
cho 4 đơn vị: Vườn Sáng Tạo, Victoria, Gấu Panda, Đại Dương Xanh.

## Tình trạng hiện tại

Repo đang ở **giai đoạn 2**: đã có website nhập liệu tiếng Việt chạy được
trên máy tính và điện thoại, tạo ra PDF thử nghiệm.
Chưa có đăng nhập, database, OCR hay chức năng phát hành chính thức.

Mọi PDF do chương trình tạo ra đều mang dòng
`BẢN THỬ NGHIỆM DỮ LIỆU GIẢ CHƯA DÙNG KÝ` và **không dùng để ký thật**.

## Nội dung repo

| Thư mục | Nội dung |
| --- | --- |
| `contract_kit/` | Phần lõi thử nghiệm: mẫu Word, cấu hình 4 đơn vị, bộ tính lương |
| `backend/` | Máy chủ FastAPI, bọc phần lõi thành API |
| `frontend/` | Website React TypeScript cho nhân sự nhập liệu |
| `docs/` | Bản kế hoạch/đặc tả đầy đủ của ứng dụng |

Backend không định nghĩa lại quy tắc nghiệp vụ. Mức lương, thông tin đơn vị
và chính sách khấu trừ đều đọc từ `contract_kit/config` nên chỉ có một nguồn
sự thật.

Chi tiết từng file xem `contract_kit/README.md`.
Bản đồ 51 biến và các điểm cần chốt xem `contract_kit/Ban_do_truong_va_cac_diem_can_chot.md`.

## Yêu cầu môi trường

- Python 3.11 trở lên
- LibreOffice **kèm gói Writer** (`libreoffice-writer`) — thiếu gói này sẽ
  báo lỗi `Không chuyển được Word sang PDF`
- Font hỗ trợ tiếng Việt, nên cài đúng các font mà mẫu Word đang dùng

## Cách chạy website

Cần hai cửa sổ dòng lệnh.

```bash
# Cửa sổ 1 — máy chủ
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload --app-dir backend --port 8000
```

```bash
# Cửa sổ 2 — giao diện
cd frontend
npm install
npm run dev
```

Mở `http://localhost:5173`. Bấm **Điền hồ sơ mẫu để thử** để thử nhanh toàn
bộ luồng mà không phải gõ tay.

Muốn chạy bằng một cổng duy nhất thì build giao diện trước; máy chủ sẽ tự
phục vụ file tĩnh tại `http://localhost:8000`:

```bash
cd frontend && npm run build && cd ..
.venv/bin/python -m uvicorn app.main:app --app-dir backend --port 8000
```

### Các endpoint

| Phương thức | Đường dẫn | Công dụng |
| --- | --- | --- |
| GET | `/api/health` | Kiểm tra máy chủ sống |
| GET | `/api/units` | 4 đơn vị đã cấu hình |
| GET | `/api/positions` | 5 vị trí và mức lương cơ bản |
| GET | `/api/defaults` | Giá trị gợi ý cho các ô dài |
| POST | `/api/preview` | Tính lương, không tạo file |
| POST | `/api/generate` | Trả về PDF |

Xem tài liệu API tự sinh tại `http://localhost:8000/docs`.

## Cách chạy riêng phần lõi

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

## Kiểm thử

```bash
# Phần lõi (19 bài)
cd contract_kit && ../.venv/bin/python -m unittest test_core.py && cd ..

# API (20 bài)
.venv/bin/python -m unittest discover -s backend/tests -t backend

# Giao diện: kiểm tra kiểu dữ liệu và build
cd frontend && npx tsc --noEmit -p tsconfig.app.json && npm run build
```

## Bước tiếp theo

Xem mục 18 (lộ trình) và mục 22 (những thông tin còn cần chốt) trong
`docs/Ke_hoach_ung_dung_hop_dong_4_co_so.md`.

Phần chưa làm, theo thứ tự ưu tiên trong đặc tả:

1. Đăng nhập và phân quyền theo đơn vị
2. Database lưu hồ sơ nhân viên, không phải nhập lại mỗi lần
3. Đọc ảnh giấy tờ bằng OCR để giảm thao tác nhập
4. Luồng phát hành chính thức: đánh số, snapshot, chống phát hành trùng

Trước khi dùng cho hồ sơ thật còn phải chốt công thức bảo hiểm/thuế áp dụng
thực tế và rà soát điều khoản theo từng đơn vị và chức danh.
