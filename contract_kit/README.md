# Bộ khởi đầu tạo hợp đồng cho 4 đơn vị

Bộ này chứng minh luồng dữ liệu JSON → hai tài liệu Word → một PDF gồm hợp đồng, phụ lục lương và thỏa thuận trách nhiệm. Mẫu được tạo từ hai file người dùng cung cấp. Đã cấu hình Vườn Sáng Tạo, Victoria, Gấu Panda và Đại Dương Xanh.

Đây là phần lõi thử nghiệm để đưa vào ứng dụng sau này. Chưa có website, tài khoản, OCR, database, đánh số chính thức hoặc luồng duyệt. Mọi PDF do chương trình tạo đều có dòng BẢN THỬ NGHIỆM DỮ LIỆU GIẢ CHƯA DÙNG KÝ. Cần chốt công thức, điều khoản và phạm vi mẫu trước khi xây chức năng phát hành thật.

## Nội dung

| File | Mục đích |
| --- | --- |
| `generate_demo.py` | Chương trình chạy thử từ JSON sang PDF |
| `salary_engine.py` | Tính Gross/Net và tìm Gross theo hàm khấu trừ được cung cấp |
| `config/business_rules.json` | Ngày ký bắt buộc nhập tay, mức cơ bản theo vị trí và hai kiểu lương |
| `config/units.json` | Thông tin 4 đơn vị theo nội dung người dùng cung cấp |
| `config/field_map.json` | 51 biến và vị trí tương ứng trong mẫu |
| `config/template_manifest.json` | Bộ tài liệu, dấu vết nguồn và trạng thái mẫu |
| `config/salary_policy_example.json` | Các tỷ lệ suy ra để tái hiện số liệu mẫu |
| `examples/employee_demo.json` | Một hồ sơ giả, không chứa căn cước người trong file nguồn |
| `examples/employee_net_demo.json` | Cùng hồ sơ giả, nhập Net 6.000.000 để thử chiều tính ngược |
| `templates/Hop_dong_va_phu_luc_template.docx` | Hợp đồng và phụ lục trong một Word |
| `templates/Thoa_thuan_trach_nhiem_template.docx` | Thỏa thuận trách nhiệm |
| `Ban_do_truong_va_cac_diem_can_chot.md` | Bản đồ trường và các khác biệt cần giải quyết |
| `test_core.py` | Kiểm tra phép tính, các đơn vị và lỗi đầu vào quan trọng |
| `requirements.txt` | Các thư viện đã dùng để kiểm thử |

## Chạy thử

Cần Python, LibreOffice và font có hỗ trợ tiếng Việt. Cài cùng các font mà mẫu Word đang dùng để hạn chế thay đổi bố cục. Kiểm thử ở môi trường này dùng lxml 6.1.1, pypdf 6.10.0 và reportlab 4.4.9.

```bash
python -m pip install -r requirements.txt
python -m unittest test_core.py
python generate_demo.py --unit dai_duong_xanh --output out/Bo_hop_dong_thu.pdf
```

Chỉ xem phép tính, không cần chuyển Word/PDF:

```bash
python generate_demo.py --calculate-only
python generate_demo.py --calculate-only --input examples/employee_net_demo.json
```

Để xuất PDF theo Net, thêm `--input examples/employee_net_demo.json` vào lệnh tạo PDF.

Chọn đơn vị bằng một trong các giá trị `vuon_sang_tao`, `victoria`, `gau_panda`, `dai_duong_xanh`. Các mã ngắn VST, VIC và GPD là gợi ý kỹ thuật; mã BDM đã có trong file nguồn.

Trên Windows, nếu LibreOffice không nằm trong PATH:

```powershell
python generate_demo.py --unit dai_duong_xanh --soffice "C:\Program Files\LibreOffice\program\soffice.exe" --font "C:\Windows\Fonts\arial.ttf" --output out/Bo_hop_dong_thu.pdf
```

Thay đường dẫn nếu cài phần mềm hoặc font ở vị trí khác. Tham số `--font` là font cho dòng đánh dấu bản thử; font nội dung Word vẫn phải được cài trên máy.

Chương trình tạo PDF và file `.calculation.json` ghi lại số tiền cùng hash PDF. Các file Word đã điền được xử lý trong thư mục tạm. Tùy chọn `--docx-only-dir` dành cho lập trình viên kiểm tra định dạng, xuất file tên DEMO; các Word đó cũng chỉ là tài liệu thử nghiệm.

## Giới hạn của bộ dựng tài liệu

Để chạy thử trong môi trường hiện có, phần lõi sử dụng thay biến trực tiếp trên OOXML, giữ các run quanh đoạn thay. Nó chỉ hỗ trợ biến có tên dạng `{{ employee.full_name }}`. Không hỗ trợ điều kiện, vòng lặp, biểu thức, bộ lọc hoặc thực thi mã trong mẫu. Không được coi đây là trình chạy Jinja đầy đủ.

Khi xây ứng dụng chính thức, có thể sử dụng docxtpl theo đặc tả hoặc tiếp tục bộ thay biến giới hạn nếu mẫu vẫn chỉ cần biến đơn. Phải kiểm thử lại khi thay engine. Không đưa file Word tùy ý của người dùng vào thực thi như mã nguồn.

Hai mẫu trong gói đã được chuẩn hóa để điền biến và kiểm tra bằng hồ sơ giả. Những tag chưa điền có thể dài hơn giá trị thật, nên kiểm tra bố cục trên bản được render với dữ liệu phù hợp. Không thêm chữ hoặc đổi định dạng bên trong tag nếu chưa hiểu cấu trúc mẫu.

## Những thay đổi có chủ đích trên bản sao

1. Thông tin người lao động trong file nguồn được chuyển thành biến. Hồ sơ thử sử dụng số giấy tờ gồm toàn số 0.
2. MST Đại Dương Xanh lấy từ cấu hình người dùng cung cấp: `0318961728-002`, thay cho giá trị `001` bị ghi khác trong hợp đồng nguồn.
3. Bỏ section trống nằm giữa hợp đồng và phụ lục; chỉnh lề phụ lục để có khoảng ký rõ ràng.
4. Chuyển bản sao thỏa thuận từ Letter sang A4; căn đầu trang bằng bảng hai cột không viền để quốc hiệu không xuống dòng sang cột tên đơn vị. Giữ tiêu đề mục 3.2 của hợp đồng cùng đoạn tiếp theo.
5. Tên cơ sở, đơn vị, người ký, các ngày và số tiền được liên kết với một nguồn dữ liệu.
6. Số trang thỏa thuận được tính khi render và điền lại nếu cần.
7. Ngày hiệu lực hợp đồng lấy trực tiếp từ ngày ký người dùng tự nhập. Ngày phụ lục, cam kết và trách nhiệm vẫn riêng; hồ sơ giả đặt ba nhóm đó cùng 01/08/2026 chỉ để thử, chưa tự đồng bộ cho mọi hồ sơ thật.
8. Các điều khoản nguồn, bao gồm điều khoản báo trước và trách nhiệm 20 triệu đồng, được giữ để rà soát. Chưa phê duyệt hiệu lực pháp lý và không chuyển thành công thức khấu trừ lương.

File Word gốc của người dùng không bị sửa.

## Phép tính đang kiểm thử

Mức căn cứ trong ví dụ là 5.310.000 đồng. Các tỷ lệ 21,5%, 2%, 10,5%, 1% chỉ được suy ra từ số tiền đã ghi trong phụ lục, chưa xác minh là tỷ lệ áp dụng cho từng đối tượng thực tế.

| Khoản | Kết quả tái hiện mẫu |
| --- | ---: |
| Lương cơ bản | 5.310.000 |
| Phụ cấp vị trí | 690.000 |
| Bảo hiểm bên sử dụng lao động | 1.141.650 |
| Công đoàn bên sử dụng lao động | 106.200 |
| Bảo hiểm người lao động | 557.550 |
| Công đoàn người lao động | 53.100 |
| Tổng thu nhập | 6.000.000 |
| Thực nhận trong ví dụ | 5.389.350 |

Ví dụ đặt thuế khấu trừ bằng 0 một cách tường minh để tái hiện số trong mẫu. Chương trình không tự suy luận miễn thuế và không coi thiếu dữ liệu thuế là 0. Các khoản người sử dụng lao động đóng không bị trừ vào thực nhận. Phí/đoàn phí công đoàn, căn cứ bảo hiểm, phần phụ cấp, mức trần và thuế cần được chốt riêng trước khi làm bộ tính chính thức.

## Bước tiếp theo

Chốt cách phân bổ phần ngoài lương cơ bản và công thức khấu trừ thực tế; xác định ngày áp dụng phụ lục/thỏa thuận; kiểm tra điều khoản theo đơn vị và chức danh. Sau đó nối phần lõi với giao diện, đăng nhập, API, OCR, database, lưu trữ riêng tư và chức năng phát hành theo bản đặc tả.

## Quy tắc đã xác nhận và schema 1.2

MST Đại Dương Xanh là `0318961728-002`. `signing_date` phải được nhập; ngày hiệu lực hợp đồng luôn bằng ngày đó. Không có giá trị mặc định là hôm nay và không nhận `contract.start_date` riêng.

| job.position_id | Vị trí | Lương cơ bản đồng/tháng |
| --- | --- | ---: |
| principal | Hiệu trưởng | 7.000.000 |
| preschool_teacher | Giáo viên mầm non | 5.310.000 |
| english_teacher | Giáo viên Tiếng Anh | 5.310.000 |
| nanny | Bảo mẫu | 5.310.000 |
| admissions_marketing | Tuyển sinh Marketing | 5.310.000 |

Đầu vào `job` chỉ cần `position_id`; tên vị trí và lương cơ bản lấy từ cấu hình. Chưa có mốc hiệu lực lịch sử của bảng mức cơ bản. Việc chọn vị trí để tính không xác nhận rằng mọi điều khoản giáo viên trong Word đều áp dụng cho vị trí đó.

Trong `compensation`, bỏ các trường nhập cũ `base_wage` và `position_allowance`, thay bằng:

```json
{
  "salary_mode": "net",
  "salary_amount": "6000000"
}
```

Đây là phần trích minh họa. File đầu vào đầy đủ vẫn cần hồ sơ, ngày, lịch làm việc và các căn cứ khấu trừ như hai file examples. `salary_mode` chỉ nhận `gross` hoặc `net`, bắt buộc có; `salary_amount` là số tiền nguyên đồng ở dạng chuỗi.

Nhập Gross: trừ các khoản của người lao động để ra Net. Nhập Net: tìm Gross sao cho số còn lại đúng Net đã nhập. Bộ tìm Gross tính lại hàm khấu trừ ở từng mức thử, yêu cầu hàm Net(Gross) xác định và không giảm; không tự áp dụng công thức thuế thật.

Ví dụ hiện có khai báo bảo hiểm người lao động 557.550, công đoàn 53.100 và thuế 0: Gross 6.000.000 cho Net 5.389.350; Net 6.000.000 cho Gross 6.610.650. Các khoản cố định này chỉ thuộc chính sách minh họa. Không coi thuế hoặc bảo hiểm luôn cố định khi Gross thay đổi trong thực tế.

`salary_engine.py` trả `income_above_base` chưa phân loại. Riêng chính sách thử có `residual_allocation=position_allowance_example_only` để đưa phần đó vào dòng phụ cấp của Word nguồn. Chưa chốt gộp hay chia các khoản phụ cấp cho ứng dụng thật.

Mã đã vượt qua 19 kiểm thử. Bộ Word và ví dụ PDF Gross đã bàn giao không đổi bố cục trong lần cập nhật này.
