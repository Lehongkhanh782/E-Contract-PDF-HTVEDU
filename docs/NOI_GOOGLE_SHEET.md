# Nối hệ thống hợp đồng với Google Sheet của ứng dụng nhân sự

Mục đích: nhân sự chọn tên trong danh sách có sẵn thay vì gõ lại toàn bộ
thông tin. Dữ liệu lấy từ chính Google Sheet mà ứng dụng nhân sự đang dùng,
nên hai hệ thống luôn khớp nhau.

> **Chưa nối thì ứng dụng vẫn chạy bình thường.** Khối chọn nhân viên tự
> ẩn đi, nhân sự nhập tay như trước. Nối hay không là tùy bạn.

## Trước khi bắt đầu: câu hỏi về tiền

Google Sheets API **miễn phí** trong hạn mức 300 lượt đọc mỗi phút — thừa
sức cho 4 cơ sở.

Việc *tạo tài khoản máy có phải khai thẻ hay không* thì tài liệu của Google
nói không thống nhất. **Bước 2 dưới đây chỉ mất 5 phút.** Nếu Google đòi
khai thẻ hoặc đặt cọc, bạn dừng lại ở đó, không mất gì.

---

## Bước 1. Lấy mã Sheet

Mở Google Sheet mà ứng dụng nhân sự đang dùng. Nhìn thanh địa chỉ:

```
https://docs.google.com/spreadsheets/d/1AbC_deF-123456789xyz/edit#gid=0
                                        └──────── mã Sheet ────────┘
```

Chép lại đoạn giữa `/d/` và `/edit`. Dán cả đường liên kết cũng được, hệ
thống tự cắt ra.

**Kiểm tra dòng đầu của Sheet.** Hệ thống đọc tên cột ở dòng 1 để biết cột
nào là gì. Nó nhận ra các tên sau, không phân biệt hoa thường hay dấu:

| Ô trên biểu mẫu | Tên cột nhận ra |
| --- | --- |
| Họ và tên | Họ và tên, Họ tên, Tên nhân viên, Full name |
| Mã nhân viên | Mã nhân viên, Mã NV, Employee code |
| Ngày sinh | Ngày sinh, Date of birth |
| Giới tính | Giới tính, Sex |
| Quốc tịch | Quốc tịch, Nationality |
| Số giấy tờ | Số CCCD, CCCD, CMND, Số căn cước, Số định danh |
| Ngày cấp | Ngày cấp |
| Nơi cấp | Nơi cấp |
| Địa chỉ thường trú | Nơi thường trú, Địa chỉ thường trú, Địa chỉ |
| Vị trí | Chức vụ, Vị trí, Chức danh |

Cột nào không có thì bỏ trống, nhân sự nhập tay ô đó. **Bắt buộc phải có
cột họ tên**, thiếu là hệ thống báo lỗi ngay.

## Bước 2. Tạo tài khoản máy

1. Vào <https://console.cloud.google.com>
2. Tạo một dự án mới, đặt tên ví dụ `hop-dong-htvedu`
3. Vào **APIs & Services → Library**, tìm **Google Sheets API**, bấm **Enable**
4. Vào **APIs & Services → Credentials** → **Create Credentials** →
   **Service account**
5. Đặt tên ví dụ `hop-dong`, bấm **Create and continue**, phần cấp quyền
   bỏ trống, bấm **Done**
6. Bấm vào tài khoản máy vừa tạo → tab **Keys** → **Add key** →
   **Create new key** → chọn **JSON** → **Create**

Google tải về một file `.json`.

> ## ⛔ Dừng lại đọc kỹ chỗ này
>
> File vừa tải về chứa dòng `-----BEGIN PRIVATE KEY-----`. Đó là **chìa
> khóa riêng**: ai cầm nó thì đọc và ghi được mọi Google Sheet đã chia sẻ
> cho tài khoản máy này, **không cần mật khẩu, không cần xác thực hai lớp**.
>
> **File này chỉ được đi đúng một đường: từ máy bạn vào ô Environment của
> Render.**
>
> Không gửi qua chat, Zalo, email hay Messenger — kể cả gửi cho người đang
> hỗ trợ bạn. Không đưa lên GitHub. Không lưu vào thư mục dự án.
>
> Lỡ gửi rồi thì coi như đã lộ, **phải hủy khóa và tạo khóa mới**: vào
> **Credentials → tài khoản máy → tab Keys**, xóa khóa cũ rồi **Add key →
> Create new key**. Xóa file đi là chưa đủ.

Mở file đó bằng Notepad, bên trong có dòng `"client_email": "...".` Chép
lại email đó, dạng `hop-dong@ten-du-an.iam.gserviceaccount.com`.

## Bước 3. Chia sẻ Sheet cho tài khoản máy

Mở Google Sheet → bấm **Chia sẻ** → dán email vừa chép → chọn quyền
**Người chỉnh sửa (Editor)** → **Gửi**.

Giống hệt chia sẻ cho một đồng nghiệp. Nếu Google hỏi có gửi thông báo
không thì bỏ chọn.

> Chọn **Editor** chứ không phải Viewer, để sau này ghi được lịch sử hợp
> đồng vào một tab riêng.

## Bước 4. Cắm chìa khóa vào Render

Vào Render → dịch vụ **hop-dong** → **Environment** → thêm hai biến:

| Key | Value |
| --- | --- |
| `ECONTRACT_GOOGLE_KEY` | Mở file `.json` bằng Notepad, chép **toàn bộ** nội dung, kể cả hai dấu ngoặc nhọn ở đầu và cuối |
| `ECONTRACT_SHEET_ID` | Mã Sheet lấy ở Bước 1 |

Muốn dùng một tab cụ thể thì thêm `ECONTRACT_SHEET_TAB` với tên tab. Bỏ
trống thì hệ thống dùng tab đầu tiên.

Bấm **Save Changes**, Render tự dựng lại.

## Bước 5. Kiểm tra

Sau khi dựng xong, đăng nhập vào web. Ở mục **2. Thông tin người lao động**
phải thấy khối **Chọn nhân viên đã có** với ô tìm kiếm.

Gõ tên một nhân viên, bấm vào kết quả — các ô phải tự điền.

### Nếu không thấy khối đó

Mở địa chỉ `https://hop-dong.onrender.com/api/sheets/status` trong trình
duyệt (phải đăng nhập trước). Nó nói rõ đang hỏng ở đâu:

| Nội dung trả về | Nghĩa là |
| --- | --- |
| `"configured": false` | Chưa khai đủ hai biến trên Render |
| `"error"` có chữ *từ chối truy cập* | Chưa chia sẻ Sheet cho email tài khoản máy |
| `"error"` có chữ *Không tìm thấy Sheet* | Sai `ECONTRACT_SHEET_ID` |
| `"error"` có chữ *không nhận ra cột họ tên* | Dòng đầu của Sheet chưa đặt tên cột |
| `"connected": true` kèm `employee_count` | Đã nối được |

Phần `headers` và `columns` trong đó cho biết hệ thống hiểu cột nào là gì.

---

## Những gì hệ thống làm và không làm với Sheet

**ĐỌC tab nhân sự, và GHI vào đúng một tab riêng.** Hệ thống không bao
giờ sửa hay xóa tab nhân sự của bạn. Nó chỉ thêm dòng vào tab
`LICH_SU_HOP_DONG`.

**Nhớ tạm 60 giây.** Sửa Sheet xong chờ khoảng một phút mới thấy thay đổi.

**Dữ liệu vẫn là gợi ý.** Sheet có thể cũ hoặc thiếu, nên nhân sự vẫn phải
đọc lại từng ô trước khi tạo hợp đồng. Giao diện có ghi nhắc điều này.

## Tab lịch sử hợp đồng

Mỗi lần tạo PDF thành công, hệ thống thêm một dòng vào tab
`LICH_SU_HOP_DONG`. Tab đó chưa có thì hệ thống tự tạo, bạn không phải
làm gì.

Tám cột, đúng thứ tự này:

| Cột | Nội dung |
| --- | --- |
| `Thoi_Diem` | Lúc bấm tạo hợp đồng, giờ Việt Nam, dạng `21/09/2026 10:30` |
| `Ma_Nhan_Vien` | Lấy từ ô Mã nhân viên trên biểu mẫu |
| `Ho_Ten` | Họ tên trên hợp đồng |
| `Ma_Truong` | Cơ sở đứng tên ký |
| `Loai_Hop_Dong` | Hợp đồng lao động hay Hợp đồng thử việc |
| `So_Hop_Dong` | Ví dụ `GPD/HDTV/HTV010` |
| `Ngay_Ky` | Ngày ký ghi trên hợp đồng |
| `Nguoi_Tao` | Tài khoản đã bấm nút tạo |

Nhờ tab này, lần sau chọn lại người đó trong hộp **Chọn nhân viên đã có**,
hệ thống hiện ngay nhãn *đã có hợp đồng* và liệt kê những bản đã cấp. Đó
là **lời nhắc**, không phải khóa: vẫn tạo thêm được, vì có những trường
hợp phải làm bản mới thật.

Tab này bạn mở xem, lọc, sửa hay xóa dòng bằng tay đều được như mọi tab
khác. Hệ thống chỉ thêm vào cuối.

**Nếu ghi không được**, ví dụ tài khoản máy chỉ có quyền Viewer, thì PDF
vẫn tải về bình thường — không bao giờ mất hợp đồng vì Sheet trục trặc —
nhưng màn hình sẽ hiện lời nhắc màu đỏ để bạn vào sửa lại quyền chia sẻ.

## Cảnh báo về dữ liệu cá nhân

Sheet này sẽ chứa số căn cước và địa chỉ của nhân viên. Hãy kiểm tra phần
**Chia sẻ** của Sheet: chỉ những người thật sự cần mới được vào, và đừng
đặt ở chế độ *ai có đường liên kết đều xem được*.

File khóa `.json` cho phép đọc và ghi Sheet đó. Nếu lỡ để lộ, vào Google
Cloud Console xóa khóa cũ và tạo khóa mới.
