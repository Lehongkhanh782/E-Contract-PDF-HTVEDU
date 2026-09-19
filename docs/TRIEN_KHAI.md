# Hướng dẫn đưa website lên mạng

Tài liệu này viết cho người chưa quen kỹ thuật. Làm theo đúng thứ tự.

> **Đọc trước khi bắt đầu.** Bản hiện tại vẫn là bản thử nghiệm: mọi PDF đều
> mang dấu *DỮ LIỆU GIẢ — CHƯA DÙNG KÝ*, và công thức bảo hiểm/thuế chưa
> được xác nhận. Đưa lên mạng để cả đội dùng thử thì được; chưa dùng để
> phát hành hợp đồng thật.

---

## Phần 0. Hiểu mình đang làm gì

Website này cần **một máy chủ thật sự chạy chương trình**, vì mỗi lần bấm
nút là nó phải mở file Word, điền thông tin rồi đổi sang PDF. Việc đó do
phần mềm LibreOffice làm.

Vì vậy **GitHub Pages không dùng được**. GitHub Pages chỉ đăng được trang
tĩnh, không chạy được chương trình.

Toàn bộ ứng dụng đã được đóng gói sẵn trong file `Dockerfile` ở thư mục gốc.
Bạn không cần hiểu file đó; chỉ cần biết nó là "bản đóng gói" để nhà cung cấp
tự dựng lên.

---

## Phần 1. Chuẩn bị hai chuỗi bí mật

> **Bỏ qua phần này** nếu bạn dùng Cách 1 ở Phần 3A (chạy script trong
> Cloud Shell) — script tự lo hết. Phần này dành cho Cách 2 và cho Render.

Mở phần mềm dòng lệnh trên máy bạn (Windows: bấm phím Windows, gõ
`PowerShell`, mở ra), rồi chạy trong thư mục dự án:

```powershell
.venv\Scripts\python -m app.usertool khoa-bi-mat
```

Nó in ra một dòng như `ECONTRACT_SECRET_KEY=abc...`. **Chép lại và giữ kín.**
Chuỗi này dùng để ký phiên đăng nhập. Mất nó thì mọi người bị đăng xuất;
lộ nó thì người khác giả mạo được phiên đăng nhập.

Tiếp theo tạo tài khoản cho nhân sự:

```powershell
cd backend
..\.venv\Scripts\python -m app.usertool them nhansu --ten-hien-thi "Phòng Nhân sự"
```

Tạo tài khoản chỉ được một cơ sở:

```powershell
..\.venv\Scripts\python -m app.usertool them quanly-vic --don-vi victoria
```

Lệnh này tạo ra file `backend/users.json`. **File này không được đưa lên
Git** (đã chặn sẵn). Lát nữa bạn sẽ dán nội dung của nó vào phần cấu hình
của nhà cung cấp.

Xem lại danh sách:

```powershell
..\.venv\Scripts\python -m app.usertool xem
```

---

## Phần 2. Chọn nơi đặt

| | **Google Cloud Run** | **Render** |
| --- | --- | --- |
| Giá | Miễn phí trong hạn mức, dư sức cho 4 cơ sở | Miễn phí 750 giờ/tháng |
| Có ngủ không | Không ngủ theo kiểu khó chịu, khởi động lại nhanh | Ngủ sau 15 phút, lần mở đầu chờ khoảng 1 phút |
| Bộ nhớ | Chọn được 1 GB | Cố định 512 MB, LibreOffice có thể thiếu chỗ |
| Cài đặt | Rắc rối hơn | Dễ hơn, bấm nút trên web |
| Thẻ ngân hàng | Phải khai | Phải khai |

**Khuyến nghị: Google Cloud Run**, vì LibreOffice cần nhiều bộ nhớ hơn mức
512 MB mà Render cho. Nếu bạn muốn thử cách dễ trước thì dùng Render, gặp
lỗi hết bộ nhớ thì chuyển sang Cloud Run.

---

## Phần 3A. Đặt trên Google Cloud Run (khuyến nghị)

Có hai cách. **Cách 1 nhanh hơn nhiều** và không phải cài gì lên máy Windows.

### Cách 1: chạy một câu lệnh trong Cloud Shell

Cloud Shell là cửa sổ dòng lệnh nằm ngay trong trình duyệt, Google cho dùng
miễn phí và đã cài sẵn mọi công cụ.

**Bước 1.** Vào <https://console.cloud.google.com>, đăng nhập bằng Gmail.
Khai thẻ ngân hàng để xác minh. Google không trừ tiền khi còn trong hạn mức
miễn phí, nhưng hãy vào **Billing → Budgets & alerts** đặt một cảnh báo
ngân sách cho yên tâm.

**Bước 2.** Tạo dự án mới, đặt tên ví dụ `hop-dong-htvedu`, rồi chọn dự án đó.

**Bước 3.** Bấm biểu tượng `>_` ở góc trên bên phải để mở Cloud Shell.

**Bước 4.** Dán nguyên khối lệnh sau rồi bấm Enter:

```bash
git clone https://github.com/Lehongkhanh782/E-Contract-PDF-HTVEDU.git
cd E-Contract-PDF-HTVEDU
git checkout claude/dazzling-fermat-qkjoee
bash deploy/cloudrun.sh
```

Script sẽ hỏi bạn tên tài khoản và mật khẩu đăng nhập đầu tiên, rồi tự làm
hết phần còn lại: bật dịch vụ, tạo khóa bí mật, build và dựng lên. Lần đầu
mất khoảng 5–10 phút.

Xong, nó in ra địa chỉ web dạng `https://hop-dong-xxxxx.a.run.app`.

Muốn đổi vùng hoặc bộ nhớ thì đặt biến trước khi chạy:

```bash
VUNG=us-east1 BO_NHO=2Gi bash deploy/cloudrun.sh
```

Về sau, mỗi khi có phiên bản mới, chỉ cần chạy lại:

```bash
cd ~/E-Contract-PDF-HTVEDU && git pull && bash deploy/cloudrun.sh
```

Tài khoản và khóa bí mật đã tạo vẫn được giữ nguyên.

### Cách 2: bấm nút trên giao diện web

Nếu bạn muốn tự bấm từng bước thay vì chạy script:

1. Vào **Cloud Run** → **Deploy container** → **Service**
2. Chọn **Continuously deploy from a repository** → **Set up with Cloud Build**
3. Chọn repository `E-Contract-PDF-HTVEDU` và nhánh muốn chạy
4. **Build Type** chọn **Dockerfile**, đường dẫn `/Dockerfile`
5. **Region**: chọn `us-central1`, `us-east1` hoặc `us-west1`. Hạn mức miễn
   phí chỉ áp dụng cho ba vùng này
6. **Authentication**: chọn **Allow unauthenticated invocations**. Nghe đáng
   sợ nhưng đúng — đây là để web mở được, còn việc chặn người lạ do màn hình
   đăng nhập của ứng dụng lo
7. Mở **Container(s), Volumes, Networking, Security**:
   - **Memory**: đổi thành **1 GiB**. Để 512 MB thì LibreOffice dễ thiếu bộ
     nhớ và tạo ra PDF hỏng
   - **Request timeout**: đặt **120** giây, vì tạo PDF mất 10–30 giây
   - **Maximum instances**: đặt **3** để chặn chi phí nếu bị gọi dồn dập
   - **Variables & Secrets** → thêm hai biến:

| Tên biến | Giá trị |
| --- | --- |
| `ECONTRACT_SECRET_KEY` | Chuỗi bí mật tạo ở Phần 1 |
| `ECONTRACT_USERS` | Dán **toàn bộ nội dung** file `backend/users.json` |

> Nên dùng nút **Reference a Secret** để cất hai giá trị này vào Secret
> Manager, thay vì để làm biến thường.

8. Bấm **Create** và chờ

### Gắn tên miền của bạn

Sau khi web chạy được:

```bash
gcloud beta run domain-mappings create \
  --service hop-dong --region us-central1 \
  --domain hopdong.tenmiencuaban.vn
```

Hoặc làm trên web: **Cloud Run → Manage custom domains → Add mapping**.

Google sẽ bắt xác minh quyền sở hữu tên miền, rồi đưa cho bạn vài bản ghi
DNS. Vào trang quản lý DNS của nhà cung cấp tên miền, thêm đúng các bản ghi
đó. Chờ từ 15 phút đến vài giờ. Google tự cấp chứng chỉ HTTPS miễn phí.

### Thêm tài khoản về sau

Tạo tài khoản mới trên máy bạn, rồi đẩy cả danh sách lên Secret Manager:

```bash
# Trên máy bạn
cd backend
../.venv/bin/python -m app.usertool them quanly-vic --don-vi victoria

# Rồi trong Cloud Shell, hoặc trên máy đã cài gcloud
gcloud secrets versions add econtract-users --data-file=backend/users.json
gcloud run services update hop-dong --region us-central1
```

## Phần 3B. Đặt trên Render (phương án dự phòng)

1. Vào <https://render.com>, đăng ký bằng tài khoản GitHub
2. Bấm **New** → **Web Service** → chọn repository `E-Contract-PDF-HTVEDU`
3. Phần **Language** chọn **Docker**
4. **Instance Type** chọn **Free**
5. Mục **Environment**, thêm hai biến `ECONTRACT_SECRET_KEY` và
   `ECONTRACT_USERS` giống bảng ở Phần 3A Bước 3
6. Bấm **Create Web Service**, chờ build xong
7. Gắn tên miền ở mục **Settings → Custom Domains**, rồi thêm bản ghi DNS
   theo hướng dẫn hiện trên màn hình

**Lưu ý về Render:** gói miễn phí ngủ sau 15 phút không ai dùng. Sáng mở lần
đầu sẽ phải chờ khoảng một phút. Nếu tạo PDF hay bị lỗi, gần như chắc chắn
là do 512 MB bộ nhớ không đủ cho LibreOffice — khi đó chuyển sang Cloud Run.

---

## Phần 4. Kiểm tra sau khi lên mạng

Làm đủ các bước sau, đừng bỏ bước nào:

1. Mở địa chỉ web, phải thấy **màn hình đăng nhập**, không thấy form nhập liệu
2. Gõ sai mật khẩu, phải báo *Sai tài khoản hoặc mật khẩu*
3. Sai 5 lần liên tiếp, phải bị khóa tạm
4. Đăng nhập đúng, bấm **Điền hồ sơ mẫu để thử**, rồi **Tính thử**
5. Bấm **Tạo và tải PDF**, mở file kiểm tra chữ tiếng Việt và bố cục
6. Đăng nhập bằng tài khoản giới hạn, phải **chỉ thấy đúng cơ sở của mình**
7. Kiểm tra địa chỉ web bắt đầu bằng **https://**, không phải http://

Nếu bước 5 ra file hỏng hoặc chữ bị vuông, xem mục Sự cố bên dưới.

---

## Phần 5. Các biến môi trường

| Biến | Bắt buộc | Công dụng |
| --- | --- | --- |
| `ECONTRACT_SECRET_KEY` | **Có** | Khóa ký phiên đăng nhập, ít nhất 32 ký tự. Không đặt thì mỗi lần khởi động lại mọi người bị đăng xuất |
| `ECONTRACT_USERS` | **Có** | Nội dung JSON của danh sách tài khoản |
| `ECONTRACT_USERS_FILE` | Không | Dùng thay cho biến trên nếu bạn gắn file vào máy chủ |
| `ECONTRACT_INSECURE_COOKIES` | Không | Đặt `1` để cookie đi qua HTTP. **Chỉ dùng khi chạy thử trên máy cá nhân.** Không bao giờ đặt trên mạng |
| `ECONTRACT_DEMO_FONT` | Không | Đường dẫn tới font .ttf cho dòng đánh dấu bản thử nghiệm |
| `PORT` | Không | Nhà cung cấp tự đặt. Mặc định 8000 |

---

## Phần 6. Sự cố thường gặp

**Báo `Không chuyển được Word sang PDF`**
Máy chủ thiếu gói `libreoffice-writer`. Nếu dùng Dockerfile của dự án thì
không gặp lỗi này. Nếu bạn tự cài lên máy chủ riêng, nhớ cài
`libreoffice-writer`, không phải chỉ `libreoffice-core`.

**PDF tạo ra bị hỏng hoặc quá trình bị dừng giữa chừng**
Gần như chắc chắn là thiếu bộ nhớ. Nâng lên 1 GB.

**Chữ tiếng Việt bị ô vuông**
Thiếu font. Kiểm tra `fonts-dejavu-core` và `fonts-liberation` đã được cài.
Muốn giữ đúng bố cục file Word gốc thì cài thêm chính các font mà file Word
đó dùng.

**Đăng nhập xong lại bị đẩy về màn hình đăng nhập**
Cookie bị chặn vì đang chạy HTTP. Kiểm tra địa chỉ có `https://` chưa, và
**không** đặt biến `ECONTRACT_INSECURE_COOKIES` trên máy chủ.

**Mọi người bị đăng xuất sau mỗi lần cập nhật**
Chưa đặt `ECONTRACT_SECRET_KEY`.

**Tạo PDF bị hết giờ**
Nâng thời gian chờ lên 120 giây.

---

## Phần 7. Những việc còn phải làm trước khi dùng thật

Đây không phải việc kỹ thuật, nhưng quan trọng hơn mọi thứ ở trên:

1. **Chốt công thức bảo hiểm, công đoàn và thuế** với kế toán. Các tỷ lệ
   hiện tại chỉ được suy ngược từ file phụ lục mẫu, chưa ai xác nhận
2. **Rà soát điều khoản** theo từng đơn vị và từng chức danh, gồm cả điều
   khoản trách nhiệm 20 triệu đồng trong mẫu gốc
3. **Xác nhận địa chỉ nơi làm việc** của từng cơ sở; hiện đang tạm dùng
   địa chỉ đăng ký kinh doanh
4. **Bỏ dấu bản thử nghiệm** và làm luồng phát hành chính thức: đánh số hợp
   đồng, lưu bản bất biến, chống phát hành trùng
5. **Lưu hồ sơ vào database** để không phải nhập lại mỗi lần

Chi tiết xem mục 22 trong `Ke_hoach_ung_dung_hop_dong_4_co_so.md`.
