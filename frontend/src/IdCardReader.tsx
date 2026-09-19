import { useEffect, useRef, useState } from 'react'
import { ApiError, fetchOcrStatus, readIdCard } from './api'
import type { ContractForm, OcrFields, OcrResult } from './types'

const TEN_TRUONG: Record<keyof OcrFields, string> = {
  full_name: 'Họ và tên',
  identity_number: 'Số giấy tờ',
  birth_date: 'Ngày sinh',
  gender: 'Giới tính',
  nationality: 'Quốc tịch',
  permanent_address: 'Địa chỉ thường trú',
}

type Trang_thai = { kind: 'idle' | 'busy' | 'error'; message?: string }

/**
 * Tải ảnh giấy tờ lên để máy đọc và điền sẵn các ô.
 *
 * Máy đọc hay nhầm dấu tiếng Việt, nhất là ở họ tên, nên giao diện phải
 * nói rõ đây chỉ là gợi ý và nhân sự vẫn phải đọc lại từng ô.
 */
export default function IdCardReader({
  onFilled,
  disabled,
}: {
  onFilled: (fields: Partial<ContractForm['employee']>) => void
  disabled?: boolean
}) {
  const [coTheDoc, setCoTheDoc] = useState<boolean | null>(null)
  const [nhanPdf, setNhanPdf] = useState(false)
  const [soTepToiDa, setSoTepToiDa] = useState(3)
  const [trangThai, setTrangThai] = useState<Trang_thai>({ kind: 'idle' })
  const [ketQua, setKetQua] = useState<OcrResult | null>(null)
  const oChonTep = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchOcrStatus()
      .then((s) => {
        setCoTheDoc(s.available)
        setNhanPdf(s.pdf)
        setSoTepToiDa(s.max_files)
      })
      .catch(() => setCoTheDoc(false))
  }, [])

  async function xuLy(files: File[]) {
    if (files.length > soTepToiDa) {
      setTrangThai({
        kind: 'error',
        message: `Chỉ chọn được tối đa ${soTepToiDa} tệp một lần.`,
      })
      return
    }
    setTrangThai({
      kind: 'busy',
      message:
        files.length > 1
          ? `Đang đọc ${files.length} tệp, mất khoảng ${files.length * 10} giây…`
          : 'Đang đọc, mất khoảng 10 giây…',
    })
    setKetQua(null)
    try {
      const doc = await readIdCard(files)
      setKetQua(doc)
      setTrangThai({ kind: 'idle' })

      // Chỉ điền những ô máy đọc được; ô nào không chắc thì để trống cho
      // nhân sự tự nhập, không đoán bừa.
      const dien: Partial<ContractForm['employee']> = {}
      const f = doc.fields
      if (f.full_name) dien.full_name = f.full_name
      if (f.identity_number) dien.identity_number = f.identity_number
      if (f.birth_date) dien.birth_date = f.birth_date
      if (f.gender) dien.gender = f.gender
      if (f.nationality) dien.nationality = f.nationality
      if (f.permanent_address) dien.permanent_address = f.permanent_address
      onFilled(dien)
    } catch (loi) {
      setTrangThai({
        kind: 'error',
        message: loi instanceof ApiError ? loi.message : 'Không gọi được máy chủ',
      })
    }
  }

  if (coTheDoc === false) {
    return (
      <p className="hint">
        Máy chủ chưa cài phần đọc ảnh. Nhập tay các ô bên dưới.
      </p>
    )
  }

  const dangBan = trangThai.kind === 'busy'

  return (
    <div className="field field-wide ocr-box">
      <div className="toolbar">
        <button
          type="button"
          onClick={() => oChonTep.current?.click()}
          disabled={disabled || dangBan || coTheDoc === null}
        >
          {dangBan
            ? 'Đang đọc…'
            : nhanPdf
              ? 'Tải ảnh hoặc PDF giấy tờ để điền nhanh'
              : 'Tải ảnh giấy tờ để điền nhanh'}
        </button>
        {ketQua && (
          <button
            type="button"
            className="ghost small"
            onClick={() => setKetQua(null)}
          >
            Ẩn kết quả
          </button>
        )}
      </div>

      <input
        ref={oChonTep}
        type="file"
        accept={
          nhanPdf
            ? 'image/jpeg,image/png,image/webp,application/pdf'
            : 'image/jpeg,image/png,image/webp'
        }
        hidden
        multiple
        onChange={(e) => {
          const files = Array.from(e.target.files ?? [])
          if (files.length) xuLy(files)
          // Cho phép chọn lại đúng tệp đó lần nữa.
          e.target.value = ''
        }}
      />

      <p className="hint">
        Chọn cùng lúc tối đa {soTepToiDa} tệp — nên chọn cả mặt trước và mặt
        sau.{' '}
        {nhanPdf
          ? 'Nhận ảnh JPG, PNG, WebP và tệp PDF đã quét. '
          : 'Nhận ảnh JPG, PNG hoặc WebP. '}
        Tệp chỉ được đọc rồi xóa, không lưu lại trên máy chủ.
      </p>

      {trangThai.message && trangThai.kind === 'error' && (
        <p className="alert error">{trangThai.message}</p>
      )}

      {ketQua && (
        <>
          <p className="alert warn">
            <b>Máy đọc xong — nhưng phải kiểm tra lại.</b> {ketQua.warning}
          </p>
          <table className="calc ocr-table">
            <tbody>
              {(Object.keys(TEN_TRUONG) as (keyof OcrFields)[]).map((khoa) => (
                <tr key={khoa}>
                  <th>{TEN_TRUONG[khoa]}</th>
                  <td>
                    {ketQua.fields[khoa] ?? (
                      <span className="hint">không đọc được — nhập tay</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="hint">
            Đọc được {ketQua.recognised.length}/6 ô
            {ketQua.files && ketQua.files.length > 1
              ? ` từ ${ketQua.files.length} tệp`
              : ''}
            . Các ô đọc được đã điền
            sẵn bên dưới, bạn sửa lại cho đúng rồi mới tạo hợp đồng.
          </p>
        </>
      )}
    </div>
  )
}
