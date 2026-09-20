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
  unitId,
  unitName,
  onPick,
  disabled,
}: {
  positions: Position[]
  /** Cơ sở đang chọn ở mục 1; danh sách chỉ hiện người của cơ sở này. */
  unitId: string
  unitName?: string
  onPick: (
    nhan_vien: Partial<ContractForm['employee']>,
    position_id: string | null,
    unit_id: string | null,
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

  // Mỗi cơ sở là một pháp nhân riêng, nên chỉ hiện người của cơ sở đang
  // chọn. Người mà Sheet ghi mã trường lạ thì xếp riêng chứ không bỏ hẳn,
  // để không ai bị mất khỏi danh sách vì một ô ghi sai.
  const cung_co_so = useMemo(
    () => (danh_sach ?? []).filter((nv) => nv.unit_id === unitId),
    [danh_sach, unitId],
  )
  const chua_ro_co_so = useMemo(
    () => (danh_sach ?? []).filter((nv) => !nv.unit_id),
    [danh_sach],
  )

  const ket_qua = useMemo(() => {
    const q = khongDau(tim)
    const loc = (ds: SheetEmployee[]) =>
      q
        ? ds.filter((nv) =>
            khongDau(`${nv.full_name ?? ''} ${nv.code ?? ''}`).includes(q),
          )
        : ds
    const chinh = loc(cung_co_so)
    // Chỉ mời tới nhóm chưa rõ cơ sở khi đang tìm, hoặc khi cơ sở này chưa
    // có ai — để danh sách thường ngày không bị lẫn.
    const them = q || chinh.length === 0 ? loc(chua_ro_co_so) : []
    return { chinh: chinh.slice(0, 8), them: them.slice(0, 5) }
  }, [cung_co_so, chua_ro_co_so, tim])

  // Đổi cơ sở thì bỏ chữ đang tìm, để không còn kết quả của cơ sở trước.
  useEffect(() => setTim(''), [unitId])

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

    // Máy chủ đã quy chức vụ và cơ sở về đúng tên trong cấu hình. Nếu máy
    // chủ chưa nhận ra thì thử đối chiếu thẳng tên chức vụ ở đây.
    let position_id: string | null = nv.position_id ?? null
    if (!position_id && nv.position) {
      const muc = khongDau(nv.position)
      const khop = positions.find(
        (p) => khongDau(p.title) === muc || khongDau(p.role_label) === muc,
      )
      position_id = khop ? khop.position_id : null
    }
    onPick(dien, position_id, nv.unit_id ?? null)
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
            {ket_qua.chinh.map((nv, i) => (
              <li key={`${nv.code ?? ''}-${i}`}>
                <button type="button" disabled={disabled} onClick={() => chon(nv)}>
                  <b>{nv.full_name}</b>
                  {nv.code ? <span className="hint"> · {nv.code}</span> : null}
                  {nv.position ? <span className="hint"> · {nv.position}</span> : null}
                </button>
              </li>
            ))}
            {ket_qua.chinh.length === 0 && (
              <li className="hint">
                {tim
                  ? 'Không tìm thấy ai khớp ở cơ sở này.'
                  : 'Cơ sở này chưa có ai trong Google Sheet.'}
              </li>
            )}
            {ket_qua.them.length > 0 && (
              <>
                <li className="hint sheet-group">
                  Sheet chưa ghi rõ cơ sở — kiểm tra lại cột Ma_Truong trước
                  khi chọn:
                </li>
                {ket_qua.them.map((nv, i) => (
                  <li key={`khac-${nv.code ?? ''}-${i}`}>
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => chon(nv)}
                    >
                      <b>{nv.full_name}</b>
                      {nv.code ? <span className="hint"> · {nv.code}</span> : null}
                      {nv.position ? (
                        <span className="hint"> · {nv.position}</span>
                      ) : null}
                    </button>
                  </li>
                ))}
              </>
            )}
          </ul>
          <p className="hint">
            Đang hiện {cung_co_so.length} người của{' '}
            {unitName ? <b>{unitName}</b> : 'cơ sở đang chọn'}, lấy từ Google
            Sheet dùng chung với ứng dụng nhân sự ({danh_sach.length} người
            toàn hệ thống). Sheet có thể cũ hoặc thiếu — vẫn phải đọc lại
            từng ô.
          </p>
        </>
      )}
    </div>
  )
}
