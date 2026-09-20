import { useEffect, useMemo, useState } from 'react'
import {
  ApiError,
  UnauthorizedError,
  downloadPdf,
  fetchMe,
  fetchPositions,
  fetchUnits,
  logout,
} from './api'
import { Field, Section, Select, TextArea } from './components'
import {
  demoForm,
  digitsOnly,
  emptyForm,
  formatMoney,
  moTaThoiHan,
  soThangHopDong,
} from './defaults'
import Brand, { MO_TA_PHIEN_BAN, PHIEN_BAN } from './Brand'
import EmployeePicker from './EmployeePicker'
import ProbationForm from './ProbationForm'
import IdCardReader from './IdCardReader'
import SalaryTable from './SalaryTable'
import LoginScreen from './LoginScreen'
import type { Account, ContractForm, Position, Unit } from './types'
import './App.css'

type Status = { kind: 'idle' | 'busy' | 'error' | 'done'; message?: string }

/**
 * Quyết định hiện màn hình đăng nhập hay màn hình nhập liệu.
 *
 * Lúc mở trang, hỏi máy chủ xem phiên cũ còn hiệu lực không. Chưa hỏi xong
 * thì chưa hiện gì, tránh nháy màn hình đăng nhập rồi lại biến mất.
 */
export default function App() {
  const [account, setAccount] = useState<Account | null>(null)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    fetchMe()
      .then(setAccount)
      .catch(() => setAccount(null))
      .finally(() => setChecking(false))
  }, [])

  if (checking) {
    return <p className="page loading">Đang kiểm tra phiên đăng nhập…</p>
  }
  if (!account) {
    return <LoginScreen onLoggedIn={setAccount} />
  }
  return (
    <ContractWorkspace
      account={account}
      onSignedOut={() => setAccount(null)}
    />
  )
}

function ContractWorkspace({
  account,
  onSignedOut,
}: {
  account: Account
  onSignedOut: () => void
}) {
  const [units, setUnits] = useState<Unit[]>([])
  // Câu nhắc phát hành do máy chủ quyết định, không viết cứng ở đây, để
  // giao diện không bao giờ nói sai về việc bản in có ký được hay không.
  const [notice, setNotice] = useState('')
  // Hai loại hợp đồng dùng hai biểu mẫu khác hẳn nhau nên tách hẳn ra,
  // thay vì nhét thêm nhánh if vào biểu mẫu chính thức.
  const [loaiHopDong, setLoaiHopDong] = useState<'chinh_thuc' | 'thu_viec'>(
    'chinh_thuc',
  )
  const [positions, setPositions] = useState<Position[]>([])
  const [form, setForm] = useState<ContractForm>(emptyForm)
  const [status, setStatus] = useState<Status>({ kind: 'idle' })
  const [loadError, setLoadError] = useState<string | null>(null)
  const [showSchedule, setShowSchedule] = useState(false)

  useEffect(() => {
    Promise.all([fetchUnits(), fetchPositions()])
      .then(([unitBody, positionBody]) => {
        setUnits(unitBody.units)
        setNotice(unitBody.notice)
        setPositions(positionBody.positions)
      })
      .catch((error: Error) => {
        if (error instanceof UnauthorizedError) {
          onSignedOut()
          return
        }
        setLoadError(
          `Không đọc được cấu hình từ máy chủ. ${error.message}. ` +
            'Kiểm tra backend đã chạy ở cổng 8000 chưa.',
        )
      })
  }, [onSignedOut])

  const selectedUnit = units.find((unit) => unit.unit_id === form.unit_id)
  const selectedPosition = positions.find(
    (position) => position.position_id === form.job.position_id,
  )

  /** Cập nhật một nhánh con của form mà giữ nguyên phần còn lại. */
  function patch<K extends keyof ContractForm>(
    key: K,
    value: Partial<ContractForm[K]>,
  ) {
    setForm((current) => ({
      ...current,
      [key]: { ...(current[key] as object), ...value },
    }))
  }

  function setTop<K extends keyof ContractForm>(key: K, value: ContractForm[K]) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  /**
   * Chọn vị trí thì điền luôn các căn cứ bảo hiểm và công đoàn bằng mức lương
   * cơ bản của vị trí đó. Đây chỉ là gợi ý theo hồ sơ mẫu; nhân sự vẫn sửa
   * được và phải kiểm tra lại theo từng trường hợp.
   */
  function choosePosition(positionId: string) {
    const position = positions.find((item) => item.position_id === positionId)
    setForm((current) => ({
      ...current,
      job: { position_id: positionId },
      compensation: position
        ? {
            ...current.compensation,
            insurance_base: position.base_wage,
            employer_union_base: position.base_wage,
            employee_union_base: position.base_wage,
          }
        : current.compensation,
    }))
  }

  /**
   * Sửa căn cứ bảo hiểm thì kéo theo hai căn cứ công đoàn, vì trong hồ sơ
   * mẫu ba giá trị này bằng nhau. Muốn khác nhau thì mở mục 5 sửa riêng.
   */
  function chooseInsuranceBase(value: string) {
    setForm((current) => ({
      ...current,
      compensation: {
        ...current.compensation,
        insurance_base: value,
        employer_union_base: value,
        employee_union_base: value,
      },
    }))
  }

  /**
   * Ngày ký là ngày hiệu lực hợp đồng và cũng là ngày phụ lục lương bắt
   * đầu áp dụng. Ngày kết thúc hợp đồng cũng là ngày phụ lục hết hiệu lực.
   * Vì vậy hai mốc của phụ lục không còn ô nhập riêng mà luôn đi theo.
   */
  function dongBoNgay(signing: string, ketThuc: string) {
    setForm((current) => ({
      ...current,
      signing_date: signing,
      contract: {
        ...current.contract,
        end_date: ketThuc,
        // Số tháng suy ra từ hai mốc ngày; nhân sự vẫn sửa lại câu được.
        type_term_text:
          moTaThoiHan(signing, ketThuc) ?? current.contract.type_term_text,
      },
      salary_period: { effective_from: signing, effective_to: ketThuc },
      responsibility: {
        commitment_from: signing || current.responsibility.commitment_from,
        commitment_to: ketThuc || current.responsibility.commitment_to,
        liability_from: signing || current.responsibility.liability_from,
        liability_to: ketThuc || current.responsibility.liability_to,
      },
    }))
  }

  function chooseSigningDate(value: string) {
    dongBoNgay(value, form.contract.end_date)
  }

  function chooseEndDate(value: string) {
    dongBoNgay(form.signing_date, value)
  }

  const soThang = soThangHopDong(form.signing_date, form.contract.end_date)

  const missing = useMemo(() => {
    const required: [string, string][] = [
      ['Cơ sở', form.unit_id],
      ['Họ tên nhân viên', form.employee.full_name],
      ['Mã nhân viên', form.employee.code],
      ['Ngày sinh', form.employee.birth_date],
      ['Số giấy tờ', form.employee.identity_number],
      ['Ngày cấp', form.employee.identity_issue_date],
      ['Nơi cấp', form.employee.identity_issuer],
      ['Địa chỉ thường trú', form.employee.permanent_address],
      ['Vị trí', form.job.position_id],
      ['Ngày ký', form.signing_date],
      ['Ngày kết thúc hợp đồng', form.contract.end_date],
      ['Số tiền lương', form.compensation.salary_amount],
      ['Căn cứ bảo hiểm', form.compensation.insurance_base],
    ]
    return required.filter(([, value]) => !value.trim()).map(([label]) => label)
  }, [form])

  async function runDownload() {
    setStatus({
      kind: 'busy',
      message: 'Đang dựng Word và chuyển PDF, mất khoảng 10 đến 30 giây…',
    })
    try {
      const name = await downloadPdf(form)
      setStatus({ kind: 'done', message: `Đã tải về: ${name}` })
    } catch (error) {
      if (error instanceof UnauthorizedError) {
        onSignedOut()
        return
      }
      setStatus({
        kind: 'error',
        message: error instanceof ApiError ? error.message : String(error),
      })
    }
  }

  async function signOut() {
    await logout()
    onSignedOut()
  }

  const busy = status.kind === 'busy'
  const blocked = missing.length > 0

  return (
    <div className="page">
      <header className="top">
        <div className="account-bar">
          <span>
            {account.display_name}
            {!account.all_units && (
              <span className="hint">
                {' '}
                — chỉ cơ sở: {account.units.join(', ')}
              </span>
            )}
          </span>
          <button type="button" className="ghost small" onClick={signOut}>
            Đăng xuất
          </button>
        </div>
        <Brand />
        {notice && <p className="notice">{notice}</p>}
      </header>

      {loadError && <p className="alert error">{loadError}</p>}

      <div className="toolbar loai-hop-dong">
        <button
          type="button"
          className={loaiHopDong === 'chinh_thuc' ? 'primary' : 'ghost'}
          onClick={() => setLoaiHopDong('chinh_thuc')}
          disabled={busy}
        >
          Hợp đồng chính thức
        </button>
        <button
          type="button"
          className={loaiHopDong === 'thu_viec' ? 'primary' : 'ghost'}
          onClick={() => setLoaiHopDong('thu_viec')}
          disabled={busy}
        >
          Hợp đồng thử việc
        </button>
      </div>

      {loaiHopDong === 'thu_viec' ? (
        <ProbationForm
          units={units}
          positions={positions}
          onSignedOut={onSignedOut}
        />
      ) : (
        <>
      <div className="toolbar">
        <button
          type="button"
          onClick={() => {
            // Hồ sơ mẫu gắn sẵn cơ sở Đại Dương Xanh. Tài khoản không có
            // quyền cơ sở đó thì lấy cơ sở đầu tiên được phép.
            const allowed = units.some((unit) => unit.unit_id === demoForm.unit_id)
            setForm({
              ...demoForm,
              unit_id: allowed ? demoForm.unit_id : (units[0]?.unit_id ?? ''),
            })
            setStatus({ kind: 'idle' })
          }}
          disabled={busy || units.length === 0}
        >
          Điền hồ sơ mẫu để thử
        </button>
        <button
          type="button"
          className="ghost"
          onClick={() => {
            setForm(emptyForm)
            setStatus({ kind: 'idle' })
          }}
          disabled={busy}
        >
          Xóa hết
        </button>
      </div>

      <Section title="1. Chọn cơ sở">
        <Select
          label="Cơ sở"
          required
          value={form.unit_id}
          onChange={(value) => setTop('unit_id', value)}
          options={units.map((unit) => ({
            value: unit.unit_id,
            label: `${unit.display_name} (${unit.code})`,
          }))}
        />
        {selectedUnit && (
          <div className="field field-wide readout">
            <div>
              <span className="label">Bên sử dụng lao động</span>
              {selectedUnit.legal_name}
            </div>
            <div>
              <span className="label">Mã số thuế</span>
              {selectedUnit.tax_code}
            </div>
            <div>
              <span className="label">Địa chỉ</span>
              {selectedUnit.address}
            </div>
            <div>
              <span className="label">Người ký</span>
              {selectedUnit.signatory_display} — {selectedUnit.signatory_title}
            </div>
          </div>
        )}
      </Section>

      <Section
        title="2. Thông tin người lao động"
        hint="Có thể tải ảnh giấy tờ lên để máy điền sẵn, nhưng máy hay nhầm dấu tiếng Việt nên phải đọc lại từng ô."
      >
        <EmployeePicker
          positions={positions}
          unitId={form.unit_id}
          unitName={selectedUnit?.display_name}
          disabled={busy}
          onPick={(fields, positionId, unitId) => {
            patch('employee', fields)
            if (positionId) choosePosition(positionId)
            // Chỉ đổi cơ sở sang cơ sở mà tài khoản này được phép làm.
            if (unitId && units.some((unit) => unit.unit_id === unitId)) {
              setTop('unit_id', unitId)
            }
          }}
        />
        <IdCardReader
          disabled={busy}
          onFilled={(fields) => patch('employee', fields)}
        />
        <Field
          label="Họ và tên"
          required
          value={form.employee.full_name}
          onChange={(value) => patch('employee', { full_name: value })}
        />
        <Field
          label="Mã nhân viên"
          required
          value={form.employee.code}
          onChange={(value) => patch('employee', { code: value })}
        />
        <Field
          label="Ngày sinh"
          type="date"
          required
          value={form.employee.birth_date}
          onChange={(value) => patch('employee', { birth_date: value })}
        />
        <Field
          label="Giới tính"
          value={form.employee.gender}
          onChange={(value) => patch('employee', { gender: value })}
        />
        <Field
          label="Quốc tịch"
          value={form.employee.nationality}
          onChange={(value) => patch('employee', { nationality: value })}
        />
        <Field
          label="Số CCCD / giấy tờ"
          required
          inputMode="numeric"
          hint="9 đến 12 chữ số"
          value={form.employee.identity_number}
          onChange={(value) =>
            patch('employee', { identity_number: digitsOnly(value) })
          }
        />
        <Field
          label="Ngày cấp"
          type="date"
          required
          value={form.employee.identity_issue_date}
          onChange={(value) => patch('employee', { identity_issue_date: value })}
        />
        <Field
          label="Nơi cấp"
          required
          hint="Điền sẵn Cục Cảnh sát; sửa lại nếu giấy tờ cũ do tỉnh cấp."
          value={form.employee.identity_issuer}
          onChange={(value) => patch('employee', { identity_issuer: value })}
        />
        <Field
          label="Địa chỉ thường trú"
          required
          wide
          value={form.employee.permanent_address}
          onChange={(value) => patch('employee', { permanent_address: value })}
        />
      </Section>

      <Section
        title="3. Vị trí và thời hạn"
        hint="Ngày ký là ngày hiệu lực hợp đồng và cũng là ngày phụ lục lương bắt đầu áp dụng. Số tháng tự tính từ hai mốc ngày."
      >
        <Select
          label="Vị trí"
          required
          value={form.job.position_id}
          onChange={choosePosition}
          options={positions.map((position) => ({
            value: position.position_id,
            label: `${position.title} — ${formatMoney(position.base_wage)} đ`,
          }))}
          hint={
            selectedPosition
              ? `Lương cơ bản ${formatMoney(selectedPosition.base_wage)} đ/tháng`
              : undefined
          }
        />
        <Field
          label="Ngày ký (= ngày hiệu lực)"
          type="date"
          required
          hint="Gợi ý sẵn ngày 1 theo quy tắc nửa đầu tháng; sửa lại được."
          value={form.signing_date}
          onChange={chooseSigningDate}
        />
        <Field
          label="Ngày kết thúc hợp đồng"
          type="date"
          required
          value={form.contract.end_date}
          onChange={chooseEndDate}
        />
        <Field
          label="Loại và thời hạn hợp đồng"
          wide
          hint={
            soThang === null
              ? 'Tự điền khi chọn đủ ngày ký và ngày kết thúc'
              : `Tính được ${soThang} tháng từ hai mốc ngày ở trên. Phụ lục lương cũng áp dụng đúng khoảng này.`
          }
          value={form.contract.type_term_text}
          onChange={(value) => patch('contract', { type_term_text: value })}
        />
      </Section>

      <Section
        title="4. Lương"
        hint="Chọn Gross thì hệ thống trừ ra Net. Chọn Net thì hệ thống tìm Gross tương ứng. Bảng lương bên dưới tự cập nhật theo số bạn nhập."
      >
        <Select
          label="Kiểu lương"
          required
          value={form.compensation.salary_mode}
          onChange={(value) =>
            patch('compensation', { salary_mode: value as 'gross' | 'net' })
          }
          options={[
            { value: 'gross', label: 'Gross — trước khấu trừ' },
            { value: 'net', label: 'Net — thực nhận' },
          ]}
        />
        <Field
          label="Số tiền (đồng)"
          required
          inputMode="numeric"
          hint={
            form.compensation.salary_amount
              ? `${formatMoney(form.compensation.salary_amount)} đ`
              : 'Chỉ nhập số, ví dụ 6000000'
          }
          value={form.compensation.salary_amount}
          onChange={(value) =>
            patch('compensation', { salary_amount: digitsOnly(value) })
          }
        />
        <Field
          label="Căn cứ đóng bảo hiểm"
          required
          inputMode="numeric"
          hint={
            form.compensation.insurance_base
              ? `${formatMoney(form.compensation.insurance_base)} đ — tự điền theo vị trí, sửa được`
              : 'Tự điền khi chọn vị trí'
          }
          value={form.compensation.insurance_base}
          onChange={(value) => chooseInsuranceBase(digitsOnly(value))}
        />

        <div className="field field-wide">
          <SalaryTable form={form} />
        </div>
      </Section>

      <section className="card">
        <button
          type="button"
          className="disclosure"
          onClick={() => setShowSchedule((open) => !open)}
        >
          {showSchedule ? '▾' : '▸'} 5. Khấu trừ chi tiết, lịch làm việc và kỳ
          trả lương
          <span className="hint"> (đã điền sẵn, mở ra nếu cần sửa)</span>
        </button>
        {showSchedule && (
          <div className="grid">
            <Field
              label="Căn cứ công đoàn (bên sử dụng lao động)"
              inputMode="numeric"
              value={form.compensation.employer_union_base}
              onChange={(value) =>
                patch('compensation', { employer_union_base: digitsOnly(value) })
              }
            />
            <Field
              label="Căn cứ đoàn phí (người lao động)"
              inputMode="numeric"
              value={form.compensation.employee_union_base}
              onChange={(value) =>
                patch('compensation', { employee_union_base: digitsOnly(value) })
              }
            />
            <Field
              label="Kỳ trả lương"
              wide
              value={form.payment.window_text}
              onChange={(value) => patch('payment', { window_text: value })}
            />
            <Field
              label="Nhãn ngày trong tuần"
              value={form.work_schedule.weekdays_label}
              onChange={(value) => patch('work_schedule', { weekdays_label: value })}
            />
            <Field
              label="Nhãn thứ bảy"
              value={form.work_schedule.saturday_label}
              onChange={(value) => patch('work_schedule', { saturday_label: value })}
            />
            <Field
              label="Trong tuần — sáng"
              value={form.work_schedule.weekday_morning}
              onChange={(value) => patch('work_schedule', { weekday_morning: value })}
            />
            <Field
              label="Trong tuần — chiều"
              value={form.work_schedule.weekday_afternoon}
              onChange={(value) =>
                patch('work_schedule', { weekday_afternoon: value })
              }
            />
            <Field
              label="Thứ bảy — sáng"
              value={form.work_schedule.saturday_morning}
              onChange={(value) =>
                patch('work_schedule', { saturday_morning: value })
              }
            />
            <Field
              label="Thứ bảy — chiều"
              value={form.work_schedule.saturday_afternoon}
              onChange={(value) =>
                patch('work_schedule', { saturday_afternoon: value })
              }
            />
            <TextArea
              label="Nghỉ trưa trong tuần"
              value={form.work_schedule.weekday_lunch}
              onChange={(value) => patch('work_schedule', { weekday_lunch: value })}
            />
            <TextArea
              label="Nghỉ trưa thứ bảy"
              rows={2}
              value={form.work_schedule.saturday_lunch}
              onChange={(value) => patch('work_schedule', { saturday_lunch: value })}
            />
            <Field
              label="Cam kết từ"
              type="date"
              value={form.responsibility.commitment_from}
              onChange={(value) =>
                patch('responsibility', { commitment_from: value })
              }
            />
            <Field
              label="Cam kết đến"
              type="date"
              value={form.responsibility.commitment_to}
              onChange={(value) => patch('responsibility', { commitment_to: value })}
            />
            <Field
              label="Trách nhiệm từ"
              type="date"
              value={form.responsibility.liability_from}
              onChange={(value) => patch('responsibility', { liability_from: value })}
            />
            <Field
              label="Trách nhiệm đến"
              type="date"
              value={form.responsibility.liability_to}
              onChange={(value) => patch('responsibility', { liability_to: value })}
            />
          </div>
        )}
      </section>

      <section className="card">
        <h2>6. Tạo hợp đồng</h2>
        {blocked && (
          <p className="alert warn">
            Còn thiếu: <b>{missing.join(', ')}</b>
          </p>
        )}
        <div className="toolbar">
          <button
            type="button"
            className="primary"
            onClick={runDownload}
            disabled={busy || blocked}
          >
            Tạo và tải PDF
          </button>
        </div>
        {status.message && (
          <p className={`alert ${status.kind === 'error' ? 'error' : 'info'}`}>
            {status.message}
          </p>
        )}
      </section>
        </>
      )}

      <footer className="foot">
        Mức lương từng vị trí, tỷ lệ bảo hiểm, công đoàn và cách tính thuế đã
        được kế toán xác nhận ngày 20/09/2026. Hệ thống chưa lưu lịch sử hợp
        đồng đã tạo, nên hãy tự kiểm tra tránh tạo trùng cho cùng một người.
        <br />
        <span className="version">
          Phiên bản {PHIEN_BAN} — {MO_TA_PHIEN_BAN}
        </span>
      </footer>
    </div>
  )
}
