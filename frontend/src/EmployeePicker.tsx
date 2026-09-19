import { useEffect, useMemo, useState } from 'react'
import { fetchEmployees } from './api'
import type { ContractForm, Position, SheetEmployee } from './types'

/** Bỏ dấu để tìm kiếm không phụ thuộc cách gõ. */
function khongDau(chuoi: string): string {
  return chuoi
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
}

/** Ngày trên Sheet hay ghi dd/mm/yyyy; biểu mẫu cần yyyy-mm-dd. */
function doiNgay(gia_tri: string | undefined): string | undefined {
  if (!gia_tri) return undefined
  const khop = /^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$/.exec(gia_tri.trim())
  if (khop) {
    const [, d, m, y] = khop
    return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`
  }
  return /^\d{4}-\d{2}-\d{2}$/.test(gia_tri.trim()) ? gia_tri.trim() : undefined
}

/**
 * Chọn nhân viên đã có trong Google Sheet dùng chung để điền sẵn biểu mẫu.
 *
 * Chưa nối Sheet thì khối này tự ẩn, nhân sự nhập tay như trước. Dữ liệu
 * lấy về vẫn là gợi ý: Sheet có thể cũ hoặc thiếu, nên phải đọc lại.
 */
export default function EmployeePicker({
  positions,
  onPick,
  disabled,
}: {
  positions: Position[]
  onPick: (
    nhan_vien: Partial<ContractForm['employee']>,
    position_id: string | null,
  ) => void
  disabled?: boolean
}) {
  const [danh_sach, setDanhSach] = useState<SheetEmployee[] | null>(null)
  const [tim, setTim] = useState('')
  const [loi, setLoi] = useState<string | null>(null)

  useEffect(() => {
    fetchEmployees()
      .then((r) => setDanhSach(r.employees))
      .catch((e: Error) => {
        setDanhSach([])
        // 503 nghĩa là chưa nối Sheet, không phải lỗi cần báo động.
        if (!/chưa khai|Chưa khai/i.test(e.message)) setLoi(e.message)
      })
  }, [])

  const ket_qua = useMemo(() => {
    if (!danh_sach) return []
    const q = khongDau(tim)
    if (!q) return danh_sach.slice(0, 8)
    return danh_sach
      .filter((nv) =>
        khongDau(`${nv.full_name ?? ''} ${nv.code ?? ''}`).includes(q),
      )
      .slice(0, 8)
  }, [danh_sach, tim])

  if (danh_sach === null) return null
  if (danh_sach.length === 0 && !loi) return null

  function chon(nv: SheetEmployee) {
    const dien: Partial<ContractForm['employee']> = {}
    if (nv.full_name) dien.full_name = nv.full_name
    if (nv.code) dien.code = nv.code
    if (nv.gender) dien.gender = nv.gender
    if (nv.nationality) dien.nationality = nv.nationality
    if (nv.identity_number) dien.identity_number = nv.identity_number.replace(/\D/g, '')
    if (nv.identity_issuer) dien.identity_issuer = nv.identity_issuer
    if (nv.permanent_address) dien.permanent_address = nv.permanent_address
    const sinh = doiNgay(nv.birth_date)
    if (sinh) dien.birth_date = sinh
    const cap = doiNgay(nv.identity_issue_date)
    if (cap) dien.identity_issue_date = cap

    // Chức vụ trên Sheet là chữ; đối chiếu với danh sách vị trí đã cấu hình.
    let position_id: string | null = null
    if (nv.position) {
      const muc = khongDau(nv.position)
      const khop = positions.find(
        (p) => khongDau(p.title) === muc || khongDau(p.role_label) === muc,
      )
      position_id = khop ? khop.position_id : null
    }
    onPick(dien, position_id)
    setTim('')
  }

  return (
    <div className="field field-wide sheet-box">
      <span className="label">Chọn nhân viên đã có</span>
      {loi ? (
        <p className="alert error">{loi}</p>
      ) : (
        <>
          <input
            type="search"
            placeholder="Gõ tên hoặc mã nhân viên…"
            value={tim}
            disabled={disabled}
            onChange={(e) => setTim(e.target.value)}
          />
          <ul className="sheet-list">
            {ket_qua.map((nv, i) => (
              <li key={`${nv.code ?? ''}-${i}`}>
                <button type="button" disabled={disabled} onClick={() => chon(nv)}>
                  <b>{nv.full_name}</b>
                  {nv.code ? <span className="hint"> · {nv.code}</span> : null}
                  {nv.position ? <span className="hint"> · {nv.position}</span> : null}
                </button>
              </li>
            ))}
            {ket_qua.length === 0 && (
              <li className="hint">Không tìm thấy ai khớp.</li>
            )}
          </ul>
          <p className="hint">
            Lấy từ Google Sheet dùng chung với ứng dụng nhân sự ({danh_sach.length}{' '}
            người). Sheet có thể cũ hoặc thiếu — vẫn phải đọc lại từng ô.
          </p>
        </>
      )}
    </div>
  )
}
