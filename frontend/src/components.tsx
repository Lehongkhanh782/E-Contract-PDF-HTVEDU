import type { ReactNode } from 'react'

export function Section({
  title,
  hint,
  children,
}: {
  title: string
  hint?: string
  children: ReactNode
}) {
  return (
    <section className="card">
      <h2>{title}</h2>
      {hint && <p className="hint">{hint}</p>}
      <div className="grid">{children}</div>
    </section>
  )
}

/**
 * Ô nhập ngày của trình duyệt hiển thị theo ngôn ngữ của máy, có máy ra
 * mm/dd/yyyy. Hiện thêm một dòng theo kiểu Việt Nam để nhân sự không đọc
 * nhầm ngày với tháng.
 */
function vietnameseDate(value: string): string | undefined {
  const matched = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!matched) return undefined
  const [, year, month, day] = matched
  return `Ngày ${day}/${month}/${year}`
}

/** Ô bắt buộc mà đang trống thì tô viền đỏ, để nhìn là thấy còn thiếu gì. */
function lopThieu(required: boolean | undefined, value: string): string {
  return required && !value.trim() ? ' thieu' : ''
}

export function Field({
  label,
  value,
  onChange,
  type = 'text',
  hint,
  wide,
  required,
  inputMode,
  onBlur,
}: {
  label: string
  value: string
  onChange: (next: string) => void
  type?: string
  hint?: string
  wide?: boolean
  required?: boolean
  inputMode?: 'numeric' | 'text'
  onBlur?: () => void
}) {
  return (
    <label
      className={
        (wide ? 'field field-wide' : 'field') + lopThieu(required, value)
      }
    >
      <span className="label">
        {label}
        {required && <b className="req"> *</b>}
      </span>
      <input
        type={type}
        value={value}
        inputMode={inputMode}
        onChange={(event) => onChange(event.target.value)}
        onBlur={onBlur}
      />
      {type === 'date' && vietnameseDate(value) && (
        <span className="hint">{vietnameseDate(value)}</span>
      )}
      {hint && <span className="hint">{hint}</span>}
    </label>
  )
}

export function TextArea({
  label,
  value,
  onChange,
  rows = 3,
}: {
  label: string
  value: string
  onChange: (next: string) => void
  rows?: number
}) {
  return (
    <label className="field field-wide">
      <span className="label">{label}</span>
      <textarea
        rows={rows}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  )
}

export function Select({
  label,
  value,
  onChange,
  options,
  required,
  hint,
}: {
  label: string
  value: string
  onChange: (next: string) => void
  options: { value: string; label: string }[]
  required?: boolean
  hint?: string
}) {
  return (
    <label className={'field' + lopThieu(required, value)}>
      <span className="label">
        {label}
        {required && <b className="req"> *</b>}
      </span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">— Chọn —</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {hint && <span className="hint">{hint}</span>}
    </label>
  )
}
