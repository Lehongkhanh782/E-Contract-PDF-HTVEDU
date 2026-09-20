import { useEffect, useMemo, useState } from 'react'
import {
  ApiError,
  UnauthorizedError,
  downloadProbationPdf,
  fetchPrincipals,
  tidyAddress,
} from './api'
import { Field, Section, Select } from './components'
import EmployeePicker from './EmployeePicker'
import IdCardReader from './IdCardReader'
import { formatMoney, goiYNgayKy, soThangHopDong } from './defaults'
import type { Position, ProbationForm as Form, Unit } from './types'

type Status = { kind: 'idle' | 'busy' | 'error' | 'done'; message?: string }

/** Giá trị mở đầu, lấy theo mẫu nhà trường đang dùng. */
export function bieuMauTrong(): Form {
  return {
    unit_id: '',
    employee: {
      full_name: '',
      code: '',
      birth_date: '',
      gender: 'Nữ',
      nationality: 'Việt Nam',
      hometown: '',
      identity_number: '',
      identity_issue_date: '',
      identity_issuer: 'Cục Cảnh sát',
      permanent_address: '',
    },
    job: { position_id: '', department: '', supervisor_name: '' },
    signing_date: goiYNgayKy(),
    probation: {
      start_date: goiYNgayKy(),
      end_date: '',
      full_gross: '',
      rate_percent: '85',
      work_hours: '07g00 – 17g00',
      rest_hours: '12g00 – 14g00',
    },
    payment: { window_text: 'Từ ngày 01 – ngày 05 hàng tháng' },
  }
}

/** Chỉ nhận chữ số, để người dùng gõ dấu chấm cũng không sai. */
function chiSo(value: string): string {
  return value.replace(/\D/g, '')
}

export default function ProbationForm({
  units,
  positions,
  onSignedOut,
}: {
  units: Unit[]
  positions: Position[]
  onSignedOut: () => void
}) {
  const [form, setForm] = useState<Form>(bieuMauTrong)
  const [status, setStatus] = useState<Status>({ kind: 'idle' })
  // Hiệu trưởng từng cơ sở, đọc từ Google Sheet. Chưa nối Sheet thì rỗng
  // và ô người điều hành hiện ra cho gõ tay.
  const [hieuTruong, setHieuTruong] = useState<Record<string, string>>({})
  // Lời nhắc về địa chỉ, ví dụ tên phường không còn trong danh mục mới.
  const [nhacDiaChi, setNhacDiaChi] = useState<string[]>([])
  const [linkTraCuu, setLinkTraCuu] = useState<string | null>(null)

  useEffect(() => {
    fetchPrincipals()
      .then((r) => setHieuTruong(r.principals))
      .catch(() => setHieuTruong({}))
  }, [])

  type NhomLong = 'employee' | 'job' | 'probation' | 'payment'

  function patch<K extends NhomLong>(khoa: K, gia_tri: Partial<Form[K]>) {
    setForm((cu) => ({ ...cu, [khoa]: { ...cu[khoa], ...gia_tri } }))
  }

  /** Chọn cơ sở thì điền luôn hiệu trưởng của cơ sở đó. */
  function chonCoSo(unit_id: string) {
    setForm((cu) => ({
      ...cu,
      unit_id,
      job: {
        ...cu.job,
        // Không biết hiệu trưởng cơ sở mới thì xóa trống cho ô đỏ lên.
        // Giữ lại tên của cơ sở cũ là in ra một cái tên sai mà không ai
        // để ý, nguy hơn hẳn một ô còn trống.
        supervisor_name: hieuTruong[unit_id] ?? '',
      },
    }))
  }

  /** Chọn chức danh thì điền luôn bộ phận công tác theo cấu hình. */
  function chonChucDanh(position_id: string) {
    const vi_tri = positions.find((p) => p.position_id === position_id)
    setForm((cu) => ({
      ...cu,
      job: {
        ...cu.job,
        position_id,
        // Bỏ chọn vị trí thì bộ phận cũng trống theo, vì nó suy ra từ vị trí.
        department: position_id ? (vi_tri?.department ?? '') : '',
      },
    }))
  }

  // Ngày ký chính là ngày bắt đầu thử việc, như hợp đồng chính thức.
  function chonNgayBatDau(value: string) {
    setForm((cu) => ({
      ...cu,
      signing_date: value,
      probation: { ...cu.probation, start_date: value },
    }))
  }

  const soThang = soThangHopDong(
    form.probation.start_date,
    form.probation.end_date,
  )

  // Lương thử việc tính ngay tại đây cho người nhập thấy trước khi tạo file.
  // Máy chủ vẫn tính lại bằng chính con số này, đây chỉ là xem trước.
  const luongThuViec = useMemo(() => {
    const goc = Number(form.probation.full_gross)
    const ty_le = Number(form.probation.rate_percent)
    if (!goc || !ty_le) return null
    return Math.round((goc * ty_le) / 100)
  }, [form.probation.full_gross, form.probation.rate_percent])

  const thieu = useMemo(() => {
    const can: [string, string][] = [
      ['Cơ sở', form.unit_id],
      ['Họ tên nhân viên', form.employee.full_name],
      ['Mã nhân viên', form.employee.code],
      ['Ngày sinh', form.employee.birth_date],
      ['Quê quán', form.employee.hometown],
      ['Số giấy tờ', form.employee.identity_number],
      ['Ngày cấp', form.employee.identity_issue_date],
      ['Nơi cấp', form.employee.identity_issuer],
      ['Địa chỉ thường trú', form.employee.permanent_address],
      ['Vị trí', form.job.position_id],
      ['Bộ phận công tác', form.job.department],
      ['Người điều hành trực tiếp', form.job.supervisor_name],
      ['Ngày bắt đầu', form.probation.start_date],
      ['Ngày kết thúc', form.probation.end_date],
      ['Lương chính thức', form.probation.full_gross],
    ]
    return can.filter(([, v]) => !v.trim()).map(([ten]) => ten)
  }, [form])

  /**
   * Rời khỏi ô địa chỉ thì viết lại cho đầy đủ và quy về danh mục hành
   * chính mới. Lời nhắc hiện ngay dưới ô để người nhập tự kiểm tra.
   */
  async function vietDayDuDiaChi() {
    const ket_qua = await tidyAddress(form.employee.permanent_address)
    if (ket_qua.address !== form.employee.permanent_address) {
      patch('employee', { permanent_address: ket_qua.address })
    }
    setNhacDiaChi(ket_qua.warnings)
    setLinkTraCuu(ket_qua.lookup_url ?? null)
  }

  async function taiVe() {
    setStatus({
      kind: 'busy',
      message: 'Đang dựng Word và chuyển PDF, mất khoảng 10 đến 30 giây…',
    })
    try {
      const ten = await downloadProbationPdf(form)
      setStatus({ kind: 'done', message: `Đã tải về: ${ten}` })
    } catch (loi) {
      if (loi instanceof UnauthorizedError) {
        onSignedOut()
        return
      }
      setStatus({
        kind: 'error',
        message: loi instanceof ApiError ? loi.message : String(loi),
      })
    }
  }

  const dangBan = status.kind === 'busy'
  const chan = thieu.length > 0
  const coSo = units.find((u) => u.unit_id === form.unit_id)

  return (
    <>
      <Section title="1. Chọn cơ sở">
        <Select
          label="Cơ sở"
          required
          value={form.unit_id}
          onChange={chonCoSo}
          options={units.map((u) => ({
            value: u.unit_id,
            label: u.display_name,
          }))}
        />
        {coSo && <p className="hint field-wide">{coSo.legal_name}</p>}
      </Section>

      <Section
        title="2. Thông tin người lao động"
        hint="Có thể tải ảnh giấy tờ lên để máy điền sẵn, nhưng máy hay nhầm dấu tiếng Việt nên phải đọc lại từng ô."
      >
        <EmployeePicker
          positions={positions}
          unitId={form.unit_id}
          unitName={coSo?.display_name}
          disabled={dangBan}
          onPick={(fields, positionId, unitId) => {
            patch('employee', fields as Partial<Form['employee']>)
            // Không có chức vụ thì xóa cả vị trí lẫn bộ phận công tác, chứ
            // không để lại của người vừa chọn trước đó.
            chonChucDanh(positionId ?? '')
            if (unitId && units.some((u) => u.unit_id === unitId)) {
              chonCoSo(unitId)
            }
          }}
        />
        <IdCardReader
          disabled={dangBan}
          onFilled={(fields) =>
            patch('employee', fields as Partial<Form['employee']>)
          }
        />
        <Field
          label="Họ và tên"
          required
          value={form.employee.full_name}
          onChange={(v) => patch('employee', { full_name: v })}
        />
        <Field
          label="Mã nhân viên"
          required
          hint="Dùng làm số hợp đồng thử việc."
          value={form.employee.code}
          onChange={(v) => patch('employee', { code: v })}
        />
        <Field
          label="Ngày sinh"
          type="date"
          required
          value={form.employee.birth_date}
          onChange={(v) => patch('employee', { birth_date: v })}
        />
        <Field
          label="Giới tính"
          required
          value={form.employee.gender}
          onChange={(v) => patch('employee', { gender: v })}
        />
        <Field
          label="Quê quán"
          required
          hint="Có trên CCCD. Google Sheet không có cột này nên phải gõ."
          value={form.employee.hometown}
          onChange={(v) => patch('employee', { hometown: v })}
        />
        <Field
          label="Số CCCD"
          required
          inputMode="numeric"
          value={form.employee.identity_number}
          onChange={(v) => patch('employee', { identity_number: chiSo(v) })}
        />
        <Field
          label="Ngày cấp"
          type="date"
          required
          value={form.employee.identity_issue_date}
          onChange={(v) => patch('employee', { identity_issue_date: v })}
        />
        <Field
          label="Nơi cấp"
          required
          hint="Điền sẵn Cục Cảnh sát; sửa lại nếu giấy tờ cũ do tỉnh cấp."
          value={form.employee.identity_issuer}
          onChange={(v) => patch('employee', { identity_issuer: v })}
        />
        <Field
          label="Địa chỉ thường trú"
          required
          wide
          hint="Rời khỏi ô thì hệ thống tự viết đầy đủ, bỏ chữ viết tắt."
          value={form.employee.permanent_address}
          onChange={(v) => patch('employee', { permanent_address: v })}
          onBlur={vietDayDuDiaChi}
        />
        {nhacDiaChi.length > 0 && (
          <div className="alert warn field-wide">
            {nhacDiaChi.map((n) => (
              <p key={n}>{n}</p>
            ))}
            {linkTraCuu && (
              <p>
                <a href={linkTraCuu} target="_blank" rel="noreferrer">
                  Mở trang tra cứu phường xã sau sáp nhập
                </a>
              </p>
            )}
          </div>
        )}
      </Section>

      <Section title="3. Công việc">
        <Select
          label="Chức danh chuyên môn"
          required
          value={form.job.position_id}
          onChange={chonChucDanh}
          options={positions.map((p) => ({
            value: p.position_id,
            label: p.title,
          }))}
        />
        <Field
          label="Bộ phận công tác"
          required
          hint="Tự điền theo chức danh; sửa được nếu trường hợp riêng."
          value={form.job.department}
          onChange={(v) => patch('job', { department: v })}
        />
        <Field
          label="Người điều hành trực tiếp"
          required
          wide
          hint={
            hieuTruong[form.unit_id]
              ? 'Tự điền là hiệu trưởng của cơ sở, lấy từ Google Sheet; sửa được.'
              : 'Họ tên người quản lý trực tiếp, thường là hiệu trưởng.'
          }
          value={form.job.supervisor_name}
          onChange={(v) => patch('job', { supervisor_name: v })}
        />
        <Field
          label="Thời gian làm việc"
          value={form.probation.work_hours}
          onChange={(v) => patch('probation', { work_hours: v })}
        />
        <Field
          label="Thời giờ nghỉ ngơi"
          value={form.probation.rest_hours}
          onChange={(v) => patch('probation', { rest_hours: v })}
        />
      </Section>

      <Section title="4. Thời hạn thử việc">
        <Field
          label="Ngày bắt đầu (cũng là ngày ký)"
          type="date"
          required
          value={form.probation.start_date}
          onChange={chonNgayBatDau}
        />
        <Field
          label="Ngày kết thúc"
          type="date"
          required
          value={form.probation.end_date}
          onChange={(v) => patch('probation', { end_date: v })}
        />
        <p className="hint field-wide">
          {soThang
            ? `Thời hạn hợp đồng: ${soThang} tháng.`
            : 'Chọn hai mốc ngày để hệ thống tự tính số tháng.'}
        </p>
      </Section>

      <Section
        title="5. Lương thử việc"
        hint="Thời gian thử việc chưa hưởng chế độ bảo hiểm và công đoàn, nên không có phần khấu trừ."
      >
        <Field
          label="Lương chính thức (Gross, đồng)"
          required
          inputMode="numeric"
          hint="Mức lương khi đã qua thử việc."
          value={form.probation.full_gross}
          onChange={(v) => patch('probation', { full_gross: chiSo(v) })}
        />
        <Field
          label="Tỷ lệ hưởng khi thử việc (%)"
          required
          inputMode="numeric"
          value={form.probation.rate_percent}
          onChange={(v) => patch('probation', { rate_percent: chiSo(v) })}
        />
        <Field
          label="Thời hạn trả lương"
          wide
          value={form.payment.window_text}
          onChange={(v) => patch('payment', { window_text: v })}
        />
        {luongThuViec !== null && (
          <p className="notice field-wide">
            Lương thử việc: <b>{formatMoney(String(luongThuViec))} đ</b>/tháng (
            {form.probation.rate_percent}% của{' '}
            {formatMoney(form.probation.full_gross)} đ).
          </p>
        )}
      </Section>

      <section className="card">
        <h2>6. Tạo hợp đồng thử việc</h2>
        {chan && (
          <p className="alert warn">Còn thiếu: {thieu.join(', ')}.</p>
        )}
        <button
          type="button"
          className="primary"
          disabled={dangBan || chan}
          onClick={taiVe}
        >
          {dangBan ? 'Đang tạo…' : 'Tạo và tải PDF'}
        </button>
        {status.message && (
          <p
            className={
              status.kind === 'error' ? 'alert error' : 'alert info'
            }
          >
            {status.message}
          </p>
        )}
      </section>
    </>
  )
}
