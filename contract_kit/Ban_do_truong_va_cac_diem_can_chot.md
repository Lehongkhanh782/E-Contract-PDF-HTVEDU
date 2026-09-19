# Bản đồ trường của hai mẫu Word

Đã xác định 51 biến tại 89 vị trí. Mỗi giá trị dùng chung chỉ nhập một lần. Đây là các biến đã triển khai; bộ kiểm tra nghiệp vụ đầy đủ còn bao gồm điều khoản tĩnh, quyền truy cập và hiệu lực cấu hình.

| Biến | Nguồn | Số vị trí |
| --- | --- | ---: |
| contract.end_date | Điều kiện hợp đồng | 1 |
| contract.number | Điều kiện hợp đồng | 1 |
| contract.start_date | Suy ra từ ngày ký người dùng nhập | 1 |
| contract.type_term_text | Điều kiện hợp đồng | 1 |
| display.base_wage | Lương cơ bản theo vị trí đã chọn | 2 |
| display.employee_insurance | Kết quả tính bằng code | 1 |
| display.employee_union | Kết quả tính bằng code | 1 |
| display.employer_insurance | Kết quả tính bằng code | 1 |
| display.employer_union | Kết quả tính bằng code | 1 |
| display.gross_income | Kết quả tính bằng code | 1 |
| display.net_income | Kết quả tính bằng code | 1 |
| display.position_allowance | Kết quả tính bằng code | 1 |
| employee.birth_date | Hồ sơ nhân viên đã kiểm tra | 3 |
| employee.code | Hồ sơ nhân viên đã kiểm tra | 3 |
| employee.full_name | Hồ sơ nhân viên đã kiểm tra | 4 |
| employee.gender | Hồ sơ nhân viên đã kiểm tra | 2 |
| employee.identity_issue_date | Hồ sơ nhân viên đã kiểm tra | 2 |
| employee.identity_issuer | Hồ sơ nhân viên đã kiểm tra | 2 |
| employee.identity_number | Hồ sơ nhân viên đã kiểm tra | 2 |
| employee.nationality | Hồ sơ nhân viên đã kiểm tra | 2 |
| employee.permanent_address | Hồ sơ nhân viên đã kiểm tra | 2 |
| employer.address | Cấu hình đơn vị | 6 |
| employer.header_line_1 | Cấu hình đơn vị | 1 |
| employer.header_line_2 | Cấu hình đơn vị | 1 |
| employer.institution_name | Cấu hình đơn vị | 5 |
| employer.legal_name | Cấu hình đơn vị | 7 |
| employer.parent_name | Cấu hình đơn vị | 1 |
| employer.signatory_display | Cấu hình đơn vị | 2 |
| employer.signatory_title | Cấu hình đơn vị | 2 |
| employer.signatory_upper | Cấu hình đơn vị | 1 |
| employer.tax_code | Cấu hình đơn vị | 2 |
| job.role_label | Chức danh đã xác nhận | 5 |
| job.title | Chức danh đã xác nhận | 2 |
| payment.window_text | Chính sách trả lương | 1 |
| responsibility.commitment_from | Thỏa thuận hoặc số trang | 1 |
| responsibility.commitment_to | Thỏa thuận hoặc số trang | 1 |
| responsibility.liability_from | Thỏa thuận hoặc số trang | 1 |
| responsibility.liability_to | Thỏa thuận hoặc số trang | 1 |
| responsibility.number | Thỏa thuận hoặc số trang | 1 |
| responsibility.page_count_label | Thỏa thuận hoặc số trang | 1 |
| salary.effective_from | Ngày phụ lục xác nhận | 1 |
| salary.effective_to | Ngày phụ lục xác nhận | 1 |
| signing.date_long | Ngày ký bắt buộc nhập tay | 2 |
| work_schedule.saturday_afternoon | Lịch làm việc đã duyệt | 1 |
| work_schedule.saturday_label | Lịch làm việc đã duyệt | 1 |
| work_schedule.saturday_lunch | Lịch làm việc đã duyệt | 1 |
| work_schedule.saturday_morning | Lịch làm việc đã duyệt | 1 |
| work_schedule.weekday_afternoon | Lịch làm việc đã duyệt | 1 |
| work_schedule.weekday_lunch | Lịch làm việc đã duyệt | 1 |
| work_schedule.weekday_morning | Lịch làm việc đã duyệt | 1 |
| work_schedule.weekdays_label | Lịch làm việc đã duyệt | 1 |

## 23 Cập nhật theo hai mẫu Word và thông tin đơn vị đã nhận

### Bộ tài liệu và đơn vị

File hợp đồng chứa cả hợp đồng lao động và phụ lục lương. File thứ hai là thỏa thuận trách nhiệm đi kèm. Đầu ra mục tiêu là một PDF theo thứ tự hợp đồng, phụ lục, thỏa thuận. Cả ba phần dùng cùng mã hồ sơ, đơn vị và người lao động; giữ ngày hiệu lực và số văn bản riêng khi nghiệp vụ yêu cầu.

| Hồ sơ | MST theo người dùng | Người ký được cung cấp |
| --- | --- | --- |
| Vườn Sáng Tạo | 0318573475-001 | Ông Nguyễn Văn Dũng |
| Victoria | 0318915665 | Ông Nguyễn Văn Dũng |
| Gấu Panda | 0318961728-001 | Bà Trương Thị Ngọc Mai |
| Đại Dương Xanh | 0318961728-002 | Bà Trương Thị Ngọc Mai |

Tên đầy đủ, địa chỉ và email được lưu trong config/units.json theo thông tin người dùng, chưa phải kết quả tra cứu đăng ký doanh nghiệp. Chức danh đều là Giám đốc theo nội dung được cung cấp. Tên công ty chủ quản của các chi nhánh được giữ riêng. Căn cứ ký, cách ghi đầu trang công ty chủ quản và địa điểm làm việc cần được xác nhận khi đưa vào dùng.

### Những chỗ không khớp trong nguồn

| Vị trí | Nội dung trong nguồn | Cách xử lý |
| --- | --- | --- |
| Thông tin bên A trong hợp đồng | Đại Dương Xanh nhưng MST đuôi 001 | Bản điền lấy 0318961728-002 theo thông tin mới; bản gốc giữ nguyên |
| Điều 1.1 hợp đồng | Bắt đầu 01/08/2026, kết thúc 31/05/2027 | Ngày bắt đầu lấy từ ngày ký nhập tay; ngày kết thúc vẫn riêng |
| Phụ lục mục Thời điểm áp dụng | Bắt đầu 01/03/2026 | Biến riêng; cần xác nhận có chủ đích hay còn sót từ mẫu |
| Thỏa thuận cam kết năm học | Từ 01/08/2026 đến 31/05/2027 | Biến thời gian cam kết riêng |
| Thỏa thuận đoạn bồi thường | Từ 01/06/2026 đến 31/05/2027 | Biến thời gian trách nhiệm riêng |
| Giữa hợp đồng và phụ lục | Một section trống tạo thêm trang trắng | Đã loại section trống trong bản sao làm mẫu |
| Khổ giấy | Hợp đồng A4, thỏa thuận Letter | Bản thử dùng A4 thống nhất; đầu trang thỏa thuận căn hai cột để tránh lỗi xuống dòng |
| Thỏa thuận Điều 4.1 | Ghi cứng 03 trang | Thay biến và tính lại sau render |
| Loại công việc | Giáo viên Tiếng Anh và các cam kết giáo viên | Chưa áp dụng ngầm cho mọi nhân viên |

Người dùng đã chốt ngày hiệu lực hợp đồng bằng ngày ký nhập tay. Không tự mở rộng quy tắc đó sang ngày phụ lục, cam kết và trách nhiệm khi chưa có xác nhận. Trong hồ sơ thử, ba nhóm ngày này cùng 01/08/2026 chỉ để minh họa.

### Phép tính tái hiện số trong phụ lục

Đây là suy luận số học từ tài liệu đã cung cấp, chưa phải xác nhận công thức pháp lý áp dụng cho mọi nhân viên.

| Khoản | Phép tính khớp mẫu | Giá trị đồng |
| --- | --- | ---: |
| Lương cơ bản | Giá trị đã ghi | 5.310.000 |
| Phụ cấp vị trí | Giá trị đã ghi | 690.000 |
| Bảo hiểm người sử dụng lao động | 5.310.000 × 21,5% | 1.141.650 |
| Công đoàn người sử dụng lao động | 5.310.000 × 2% | 106.200 |
| Bảo hiểm người lao động | 5.310.000 × 10,5% | 557.550 |
| Công đoàn người lao động | 5.310.000 × 1% | 53.100 |
| Tổng thu nhập | 5.310.000 + 690.000 | 6.000.000 |
| Thực nhận ghi trong mẫu | 6.000.000 − 557.550 − 53.100 | 5.389.350 |

Khoản người sử dụng lao động đóng được tách khỏi khoản khấu trừ của người lao động. Tổng chi phí theo các dòng này là 7.247.850 đồng; chỉ tiêu quản trị đó không tự thêm vào hợp đồng.

Mẫu chưa có dòng thuế TNCN cụ thể. Dữ liệu thử khai báo thuế bằng 0 để tái hiện số thực nhận; không có nghĩa nhân viên thật luôn được áp dụng thuế 0. Thiếu dữ liệu thuế phải yêu cầu bổ sung hoặc xác nhận cách tính.

Căn cứ bảo hiểm, phần phụ cấp, tư cách đoàn viên, mức trần và cách làm tròn cần xác nhận. Không suy ra mọi người đóng công đoàn 1% hoặc phụ cấp luôn là 690.000 từ một ví dụ.

### Điều khoản cần rà soát trước phát hành

Mẫu thỏa thuận có cam kết không nghỉ trước cuối năm học, khoản 20 triệu đồng cộng chi phí đào tạo và cách thu hồi khoản tiền. Hợp đồng Điều 5.4 ghi báo trước 30 ngày cho cả hai bên trong ví dụ hợp đồng 10 tháng. Cần rà soát phạm vi áp dụng với quy định về chấm dứt, đào tạo, bồi thường và khấu trừ; chưa chuyển thành quy tắc thu tiền tự động.

Điều 35 Bộ luật Lao động phân biệt thời hạn báo trước theo loại hợp đồng; Điều 102 giới hạn việc khấu trừ lương và Điều 127 quy định hành vi bị cấm trong xử lý kỷ luật. Đây là lý do cần kiểm tra chính các đoạn đã thấy trong mẫu, không phải kết luận mọi điều khoản đều vô hiệu. [Bộ luật Lao động, bản do ASEAN đăng tải](https://asean.org/wp-content/uploads/2016/08/Labor-Code-No.-45-Year-2019.pdf).

Bộ thử giữ các điều khoản để đối chiếu và ghi trạng thái mẫu draft_for_review. PDF có thông báo thử nghiệm trên mọi trang. Cần người có chuyên môn pháp luật lao động rà soát mẫu cuối trước khi dùng ký thật.

### Phần đã chuẩn bị và giới hạn

- Hai mẫu Word tự điền với 51 biến ở 89 vị trí; đã loại thông tin nhận dạng nhân viên nguồn.
- Cấu hình 4 đơn vị, hồ sơ JSON giả, chính sách tính mẫu, bản đồ trường và chương trình generate_demo.py.
- Phần lõi thử dùng thay biến OOXML giới hạn, không chạy biểu thức tùy ý. Khi đổi sang docxtpl phải kiểm thử lại.
- Kiểm tra dữ liệu 8 tổ hợp gồm 4 đơn vị × 2 mẫu; không tuyên bố đã nghiệm thu pháp lý và bố cục mọi tổ hợp.
- PDF thử Đại Dương Xanh gồm 11 trang A4: 7 trang hợp đồng, 1 trang phụ lục và 3 trang thỏa thuận; đã bỏ trang trắng thừa trên bản sao.
- Phép tính Decimal từ chối float và không coi thuế bị thiếu là 0. Không có tính năng khấu trừ khoản trách nhiệm.
- Số hợp đồng ví dụ có tiền tố DEMO. Chương trình chưa có chế độ phát hành thật hoặc các chức năng website.

### Luồng nhập phù hợp bộ mẫu

Chọn đơn vị → nhập hoặc đọc hồ sơ → chọn vị trí để lấy lương cơ bản → chọn Gross/Net và nhập số tiền → tự nhập Ngày ký / Ngày hiệu lực hợp đồng → xem ba tab Hợp đồng, Phụ lục lương, Thỏa thuận → sửa mục cần kiểm tra → tải bộ PDF. Ngày hiệu lực hợp đồng luôn lấy từ ngày ký đã nhập, không có ô nhập độc lập.

Đã chốt hỗ trợ cả Gross và Net. Phần thu nhập ngoài lương cơ bản được tính bằng Gross trừ lương cơ bản; cách phân bổ phần đó vào phụ cấp vị trí, ăn trưa, đi lại hoặc các khoản khác vẫn cần xác nhận. Bản thử chỉ đưa phần chênh vào dòng phụ cấp của mẫu khi dùng chính sách minh họa có ghi rõ giả định này.


## 24 Quy tắc đã chốt: ngày ký, vị trí và lựa chọn Gross/Net

### Dữ liệu người dùng xác nhận

| Quy tắc | Giá trị triển khai |
| --- | --- |
| MST Đại Dương Xanh | 0318961728-002 |
| Ngày ký / Ngày hiệu lực hợp đồng | Một trường bắt buộc do nhân sự tự nhập |
| Ngày hiệu lực trên Word | Luôn bằng ngày ký đã nhập |
| Lương cơ bản Hiệu trưởng | 7.000.000 đồng/tháng |
| Lương cơ bản Giáo viên mầm non | 5.310.000 đồng/tháng |
| Lương cơ bản Giáo viên Tiếng Anh | 5.310.000 đồng/tháng |
| Lương cơ bản Bảo mẫu | 5.310.000 đồng/tháng |
| Lương cơ bản Tuyển sinh Marketing | 5.310.000 đồng/tháng |
| Kiểu lương đầu vào | Bắt buộc chọn Gross hoặc Net rồi nhập số tiền |

Các mức cơ bản là quy tắc của người dùng, không phải kết luận về mức tối thiểu hay căn cứ bảo hiểm theo pháp luật. Chưa có mốc hiệu lực lịch sử của bảng lương vị trí; khi hỗ trợ hợp đồng các kỳ khác cần bổ sung phiên bản chính sách phù hợp.

### Hành vi của màn hình nhập

1. Vị trí là danh sách chọn. Chọn hoặc đổi vị trí làm cập nhật lương cơ bản từ cấu hình; không có mức dự phòng cho vị trí chưa cấu hình.
2. Chọn Gross hoặc Net. Đổi lựa chọn làm đổi nhãn ô nhập thành “Lương Gross thỏa thuận” hoặc “Lương Net thỏa thuận”; phải tính lại kết quả và bản xem trước.
3. Ngày ký / Ngày hiệu lực hợp đồng là một ô ngày để trống lúc bắt đầu. Nhân sự tự gõ hoặc chọn ngày; không tự lấy ngày hôm nay, ngày từ ảnh hay ngày của hồ sơ cũ. Ngày kết thúc là trường riêng.
4. Cột kết quả hiện lương cơ bản, Gross, từng khoản người lao động đóng, Net và phần ngoài lương cơ bản. Khoản người sử dụng lao động đóng hiển thị riêng.
5. Chưa đủ công thức khấu trừ hoặc phân bổ thì vẫn lưu được thỏa thuận Gross/Net; đánh dấu kết quả chưa hoàn chỉnh và chưa phát hành bản thật.

Đã xác nhận đồng bộ ngày ký với ngày hiệu lực của hợp đồng. Ngày phụ lục, cam kết năm học và thời gian trách nhiệm vẫn là dữ liệu riêng; không coi câu xác nhận đó là chấp thuận sửa mọi mốc ngày trong bộ tài liệu.

### Logic tính

Gọi D(g) là tổng khoản người lao động phải trừ ứng với mức Gross g, được tính từ chính sách, hồ sơ và kỳ áp dụng đã cấu hình.

- Nhập Gross g: Net = g − D(g).
- Nhập Net n: tìm Gross g sao cho g − D(g) = n. Mỗi lần thử g phải tính lại các khoản phụ thuộc vào g. Không cộng một con số thuế của mức lương khác vào n.
- Khoản người sử dụng lao động đóng không nằm trong D(g).
- Phần ngoài lương cơ bản = Gross − lương cơ bản theo vị trí. Việc ghi toàn bộ phần đó là “phụ cấp vị trí” chưa được xác nhận.
- Gross dưới lương cơ bản, Net không thể quy đổi chính xác hoặc dữ liệu còn thiếu phải báo lỗi cụ thể.

Mã salary_engine.py nhận một hàm khấu trừ từ bên ngoài. Bộ tìm Gross hoạt động với hàm Net(Gross) xác định, không giảm, số tiền nguyên đồng và có nghiệm chính xác. Bộ tính thuế thật còn cần cung cấp và kiểm thử theo từng đối tượng; mã không chứa biểu thuế pháp luật.

Trong generate_demo.py, chính sách minh họa sử dụng các căn cứ được nhập tường minh, tỷ lệ của ví dụ cũ và thuế cố định khai báo sẵn. Đây chỉ là đường chạy thử để kiểm tra hai kiểu đầu vào. Hàm tính chính thức phải thay phần chính sách minh họa khi được cung cấp.

| Ví dụ giáo viên, chỉ theo chính sách minh họa | Nhập Gross 6.000.000 | Nhập Net 6.000.000 |
| --- | ---: | ---: |
| Lương cơ bản theo vị trí | 5.310.000 | 5.310.000 |
| Gross kết quả | 6.000.000 | 6.610.650 |
| Bảo hiểm người lao động trong ví dụ | 557.550 | 557.550 |
| Công đoàn người lao động trong ví dụ | 53.100 | 53.100 |
| Thuế khai báo để thử | 0 | 0 |
| Net kết quả | 5.389.350 | 6.000.000 |
| Phần ngoài lương cơ bản | 690.000 | 1.300.650 |

Không dùng bảng trên làm báo giá lương thực tế trước khi xác nhận chính sách. Hồ sơ nhân viên thật có thể có kết quả khác khi công thức thay đổi.

### Mã và dữ liệu đã cập nhật

- config/business_rules.json chứa năm vị trí, mức cơ bản, hai chế độ lương và quy tắc một ngày nhập tay.
- examples/employee_demo.json dùng Gross 6.000.000; examples/employee_net_demo.json dùng Net 6.000.000.
- Schema thử 1.2 bỏ contract.start_date, compensation.base_wage và compensation.position_allowance khỏi đầu vào. Thay bằng signing_date, job.position_id, compensation.salary_mode và compensation.salary_amount. Không cần sửa tên biến trong Word.
- Bản đồ vẫn có 51 biến ở 89 vị trí; contract.start_date và signing.date_long cùng lấy từ signing_date.
- 19 kiểm thử đã đạt, bao gồm mức cơ bản từng vị trí, ngày bắt buộc và đồng bộ, Gross/Net, tính ngược với hàm khấu trừ phụ thuộc Gross, thiếu thuế, vị trí chưa cấu hình và dữ liệu hai mẫu của bốn đơn vị.
- PDF đã bàn giao trước vẫn là ví dụ Gross 6.000.000 đồng. Lần cập nhật này thay mã và tài liệu; không thay file PDF đó thành ví dụ Net.

### Nội dung cần bổ sung tiếp

Ưu tiên xác định cách chia phần ngoài lương cơ bản: gộp hết vào một dòng phụ cấp vị trí hay chia thành các khoản cụ thể. Sau đó cung cấp căn cứ, tỷ lệ, điều kiện bảo hiểm/công đoàn/thuế và quy tắc làm tròn để hoàn thiện cả hai chiều Gross/Net. Không cần hỏi lại lựa chọn kiểu lương hay mức lương cơ bản đã xác nhận.


## Ghi chú kỹ thuật

Chỉ số đoạn trong JSON bắt đầu từ 0, tính cả đoạn trong bảng của phần thân Word gốc. Đây là bằng chứng lúc lập mẫu, không phải tọa độ ổn định sau khi sửa Word. Chương trình chạy theo tên biến; đổi mẫu cần kiểm tra lại hash, biến thiếu và bản render.
