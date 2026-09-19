# E-Contract-PDF-HTVEDU

Ứng dụng tạo hợp đồng lao động, phụ lục lương và thỏa thuận trách nhiệm
cho 4 đơn vị: Vườn Sáng Tạo, Victoria, Gấu Panda, Đại Dương Xanh.

## Tình trạng hiện tại

Repo đang ở **giai đoạn 2**: đã có website nhập liệu tiếng Việt chạy được
trên máy tính và điện thoại, có đăng nhập và phân quyền theo cơ sở, tạo ra
PDF thử nghiệm, và đã đóng gói sẵn để đưa lên mạng.
Chưa có database lưu hồ sơ, OCR hay chức năng phát hành chính thức.

Mọi PDF do chương trình tạo ra đều mang dòng
`BẢN THỬ NGHIỆM DỮ LIỆU GIẢ CHƯA DÙNG KÝ` và **không dùng để ký thật**.

## Nội dung repo

| Thư mục | Nội dung |
| --- | --- |
| `contract_kit/` | Phần lõi thử nghiệm: mẫu Word, cấu hình 4 đơn vị, bộ tính lương |
| `backend/` | Máy chủ FastAPI, bọc phần lõi thành API |
| `frontend/` | Website React TypeScript cho nhân sự nhập liệu |
| `docs/` | Bản kế hoạch/đặc tả và hướng dẫn triển khai |
| `Dockerfile` | Bản đóng gói để chạy trên máy chủ bất kỳ |

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

## Tài khoản

Không có tài khoản mặc định. Phải tự tạo trước khi đăng nhập được:

```bash
cd backend
../.venv/bin/python -m app.usertool them nhansu --ten-hien-thi "Phòng Nhân sự"

# Tài khoản chỉ được một cơ sở
../.venv/bin/python -m app.usertool them quanly-vic --don-vi victoria

# Xem danh sách, đổi mật khẩu, sinh khóa ký phiên
../.venv/bin/python -m app.usertool xem
../.venv/bin/python -m app.usertool doi-mat-khau nhansu
../.venv/bin/python -m app.usertool khoa-bi-mat
```

Lệnh trên tạo `backend/users.json`, chỉ chứa mã băm scrypt, không chứa mật
khẩu gốc. File này đã được loại khỏi Git và không được đưa lên.

## Cách chạy website

Cần hai cửa sổ dòng lệnh.

```bash
# Cửa sổ 1 — máy chủ
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt

# ECONTRACT_INSECURE_COOKIES chỉ dùng khi chạy thử ở máy cá nhân qua HTTP.
# Không bao giờ đặt biến này trên máy chủ thật.
ECONTRACT_INSECURE_COOKIES=1 \
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
| POST | `/api/login` | Đăng nhập |
| POST | `/api/logout` | Đăng xuất |
| GET | `/api/me` | Tài khoản hiện tại và phạm vi cơ sở |
| GET | `/api/health` | Kiểm tra máy chủ sống (không cần đăng nhập) |
| GET | `/api/units` | 4 đơn vị đã cấu hình |
| GET | `/api/positions` | 5 vị trí và mức lương cơ bản |
| GET | `/api/defaults` | Giá trị gợi ý cho các ô dài |
| POST | `/api/preview` | Tính lương, không tạo file |
| POST | `/api/generate` | Trả về PDF |

Trừ `/api/health`, mọi endpoint đều yêu cầu đăng nhập. Phạm vi cơ sở được
kiểm tra lại ở máy chủ, không tin mã đơn vị mà trình duyệt gửi lên.

Xem tài liệu API tự sinh tại `http://localhost:8000/docs`.

## Đưa lên mạng

Xem hướng dẫn từng bước tại **[`docs/TRIEN_KHAI.md`](docs/TRIEN_KHAI.md)**,
gồm cả cách gắn tên miền riêng.

Chạy bằng Docker ở máy cá nhân:

```bash
docker build -t econtract .
docker run --rm -p 8000:8000 \
  -e ECONTRACT_SECRET_KEY="$(openssl rand -base64 48)" \
  -e ECONTRACT_USERS="$(cat backend/users.json)" \
  -e ECONTRACT_INSECURE_COOKIES=1 \
  econtract
```

Máy chủ cần ít nhất **1 GB bộ nhớ**; 512 MB thường không đủ cho LibreOffice.

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

Mỗi lần đẩy code lên GitHub, quy trình trong `.github/workflows/ci.yml` tự
chạy lại toàn bộ kiểm thử, tạo PDF thật cho cả 4 đơn vị và build image
Docker.

## Bước tiếp theo

Xem mục 18 (lộ trình) và mục 22 (những thông tin còn cần chốt) trong
`docs/Ke_hoach_ung_dung_hop_dong_4_co_so.md`.

Phần chưa làm, theo thứ tự ưu tiên trong đặc tả:

1. Database lưu hồ sơ nhân viên, không phải nhập lại mỗi lần
2. Đọc ảnh giấy tờ bằng OCR để giảm thao tác nhập
3. Luồng phát hành chính thức: đánh số, snapshot, chống phát hành trùng
4. Ghi lại lịch sử thao tác của từng tài khoản

Trước khi dùng cho hồ sơ thật còn phải chốt công thức bảo hiểm/thuế áp dụng
thực tế và rà soát điều khoản theo từng đơn vị và chức danh.
