import type { ContractForm } from './types'

/**
 * Giá trị khởi tạo của form.
 *
 * Phần lịch làm việc, thời hạn và kỳ trả lương lấy từ hồ sơ mẫu của
 * contract_kit để nhân sự đỡ gõ lại. Đây là gợi ý điền nhanh, chưa phải
 * điều khoản đã duyệt cho mọi vị trí và mọi đơn vị; phải đọc lại trước khi
 * dùng cho hồ sơ thật.
 */
export const emptyForm: ContractForm = {
  unit_id: '',
  employee: {
    full_name: '',
    code: '',
    birth_date: '',
    gender: 'Nữ',
    nationality: 'Việt Nam',
    identity_number: '',
    identity_issue_date: '',
    identity_issuer: '',
    permanent_address: '',
  },
  job: { position_id: '' },
  signing_date: goiYNgayKy(),
  contract: {
    type_term_text: 'Hợp đồng lao động xác định thời hạn 10 tháng',
    end_date: '',
  },
  salary_period: { effective_from: '', effective_to: '' },
  responsibility: {
    commitment_from: '',
    commitment_to: '',
    liability_from: '',
    liability_to: '',
  },
  compensation: {
    insurance_base: '',
    employer_union_base: '',
    employee_union_base: '',
    salary_mode: 'gross',
    salary_amount: '',
  },
  work_schedule: {
    weekdays_label: 'Từ ngày thứ 2 đến ngày thứ 6:',
    weekday_morning: 'Sáng: Từ 7:00 đến 12:00',
    weekday_afternoon: 'Chiều: Từ 14:00 đến 17:00',
    saturday_label: 'Ngày thứ 7 (Tối đa 2 ngày/tháng):',
    saturday_morning: 'Sáng: Từ 7:30 đến 11:30',
    saturday_afternoon: 'Chiều: Từ 13:00 đến 17:00',
    weekday_lunch:
      'Thứ 2 đến Thứ 6: Từ 12:00 đến 14:00; (Bộ phận Giáo viên sẽ thay nhau nghỉ trưa theo sự phân công của Ban giám hiệu nhằm đảm bảo an toàn cho trẻ.)',
    saturday_lunch: 'Thứ 7 (Tối đa 2 ngày/tháng): Từ 11:30 đến 13:00.',
  },
  payment: { window_text: 'từ ngày 01 đến ngày 05 hàng tháng' },
}

/** Hồ sơ giả dùng để thử nhanh toàn bộ luồng, không phải người thật. */
export const demoForm: ContractForm = {
  ...emptyForm,
  unit_id: 'dai_duong_xanh',
  employee: {
    full_name: 'Nguyễn Thị Minh An',
    code: 'NV-DEMO-001',
    birth_date: '1999-01-01',
    gender: 'Nữ',
    nationality: 'Việt Nam',
    identity_number: '000000000000',
    identity_issue_date: '2025-01-01',
    identity_issuer: 'Cơ quan cấp giấy tờ minh họa',
    permanent_address: 'Địa chỉ nhân viên minh họa, Thành phố Hồ Chí Minh',
  },
  job: { position_id: 'english_teacher' },
  signing_date: '2026-08-01',
  contract: {
    type_term_text: 'Hợp đồng lao động xác định thời hạn 10 tháng',
    end_date: '2027-05-31',
  },
  salary_period: { effective_from: '2026-08-01', effective_to: '2027-05-31' },
  responsibility: {
    commitment_from: '2026-08-01',
    commitment_to: '2027-05-31',
    liability_from: '2026-08-01',
    liability_to: '2027-05-31',
  },
  compensation: {
    insurance_base: '5310000',
    employer_union_base: '5310000',
    employee_union_base: '5310000',
    salary_mode: 'gross',
    salary_amount: '6000000',
  },
}

/**
 * Gợi ý ngày ký theo quy tắc đã chốt.
 *
 * Trong nửa đầu tháng thì gợi ý ký từ ngày 1 của chính tháng đó; từ ngày
 * 16 trở đi thì gợi ý ký từ ngày 1 tháng sau. Chỉ là gợi ý, nhân sự sửa
 * lại được.
 */
export function goiYNgayKy(homNay = new Date()): string {
  const nam = homNay.getFullYear()
  const thang = homNay.getMonth()
  const sang_thang_sau = homNay.getDate() > 15
  const ngay = new Date(nam, sang_thang_sau ? thang + 1 : thang, 1)
  return [
    ngay.getFullYear(),
    String(ngay.getMonth() + 1).padStart(2, '0'),
    '01',
  ].join('-')
}

/**
 * Số tháng của hợp đồng, tính cả ngày đầu và ngày cuối.
 *
 * Từ 01/08/2026 đến 31/05/2027 là 10 tháng: cộng một ngày vào ngày kết
 * thúc rồi mới đếm, nên mốc cuối tháng ra số tròn.
 */
export function soThangHopDong(tuNgay: string, denNgay: string): number | null {
  if (!tuNgay || !denNgay) return null
  const dau = new Date(tuNgay)
  const cuoi = new Date(denNgay)
  if (Number.isNaN(dau.getTime()) || Number.isNaN(cuoi.getTime())) return null
  if (cuoi < dau) return null

  const sau = new Date(cuoi)
  sau.setDate(sau.getDate() + 1)
  let thang =
    (sau.getFullYear() - dau.getFullYear()) * 12 +
    (sau.getMonth() - dau.getMonth())
  if (sau.getDate() < dau.getDate()) thang -= 1
  return thang > 0 ? thang : null
}

/** Câu mô tả loại hợp đồng, điền sẵn theo số tháng tính được. */
export function moTaThoiHan(tuNgay: string, denNgay: string): string | null {
  const thang = soThangHopDong(tuNgay, denNgay)
  return thang === null
    ? null
    : `Hợp đồng lao động xác định thời hạn ${thang} tháng`
}

/** 5.310.000 -> "5.310.000". Chuỗi rỗng hoặc không phải số thì trả nguyên. */
export function formatMoney(value: string): string {
  if (!/^\d+$/.test(value)) return value
  return value.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

/** Bỏ mọi ký tự không phải số, để người dùng gõ dấu chấm thoải mái. */
export function digitsOnly(value: string): string {
  return value.replace(/\D/g, '')
}
