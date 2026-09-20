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
  // Chọn xong thì thu hộp lại; bấm vào ô tìm mới sổ ra.
  const [dangMo, setDangMo] = useState(false)
  const [daChon, setDaChon] = useState<SheetEmployee | null>(null)
  // Sheet có những cột nào. Cần biết để lúc chọn người mới thì xóa đúng
  // các ô mà Sheet phụ trách, không đụng vào ô Sheet không có.
  const [cotCoTrongSheet, setCotCoTrongSheet] = useState<string[]>([])

  useEffect(() => {
    fetchEmployees()
      .then((r) => {
        setDanhSach(r.employees)
        setCotCoTrongSheet(Object.keys(r.columns ?? {}))
      })
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
    // Hộp chỉ cao bằng 5 dòng rồi cuộn, nên đưa ra nhiều hơn 5 cũng được.
    return { chinh: chinh.slice(0, 50), them: them.slice(0, 20) }
  }, [cung_co_so, chua_ro_co_so, tim])

  // Đổi cơ sở thì bỏ chữ đang tìm và thu hộp, để không còn kết quả cũ.
  useEffect(() => {
    setTim('')
    setDangMo(false)
  }, [unitId])

  if (danh_sach === null) return null
  if (danh_sach.length === 0 && !loi) return null

  function chon(nv: SheetEmployee) {
    // Ô nào Sheet phụ trách thì luôn ghi đè, kể cả khi người này bỏ trống ô
    // đó: để trống rồi tô đỏ vẫn hơn là giữ lại dữ liệu của người vừa chọn
    // trước đó, vì như vậy hợp đồng in ra lẫn thông tin của hai người.
    // Ô Sheet không có cột (quốc tịch, nơi cấp) thì không đụng tới.
    const dien: Partial<ContractForm['employee']> = {}
    const ghi = (
      truong: keyof ContractForm['employee'],
      gia_tri: string | undefined,
    ) => {
      if (cotCoTrongSheet.includes(truong)) dien[truong] = gia_tri ?? ''
    }
    ghi('full_name', nv.full_name)
    ghi('code', nv.code)
    ghi('gender', nv.gender)
    ghi('nationality', nv.nationality)
    ghi('identity_number', nv.identity_number?.replace(/\D/g, ''))
    ghi('identity_issuer', nv.identity_issuer)
    ghi('permanent_address', nv.permanent_address)
    ghi('birth_date', doiNgay(nv.birth_date))
    ghi('identity_issue_date', doiNgay(nv.identity_issue_date))

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
    setDaChon(nv)
    setDangMo(false)
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
            placeholder={
              daChon ? 'Bấm để chọn người khác…' : 'Gõ tên hoặc mã nhân viên…'
            }
            value={tim}
            disabled={disabled}
            onFocus={() => setDangMo(true)}
            onChange={(e) => {
              setTim(e.target.value)
              setDangMo(true)
            }}
          />
          {daChon && !dangMo && (
            <p className="hint da-chon">
              Đã chọn: <b>{daChon.full_name}</b>
              {daChon.code ? ` · ${daChon.code}` : ''}
            </p>
          )}
          {dangMo && (
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
          )}
          {dangMo && (
          <p className="hint">
            Đang hiện {cung_co_so.length} người của{' '}
            {unitName ? <b>{unitName}</b> : 'cơ sở đang chọn'}, lấy từ Google
            Sheet dùng chung với ứng dụng nhân sự ({danh_sach.length} người
            toàn hệ thống). Sheet có thể cũ hoặc thiếu — vẫn phải đọc lại
            từng ô.
          </p>
          )}
        </>
      )}
    </div>
  )
}
