import { useEffect, useRef, useState } from 'react'
import { ApiError, UnauthorizedError, calcSalary } from './api'
import { formatMoney } from './defaults'
import type { Calculation, ContractForm } from './types'

/** Chờ người dùng ngừng gõ rồi mới gọi máy chủ. */
const CHO_MS = 450

type Dong = { nhan: string; khoa: keyof Calculation; nhom: 'thu' | 'tru' | 'don_vi' }

const DONG: Dong[] = [
  { nhan: 'Lương cơ bản', khoa: 'base_wage', nhom: 'thu' },
  { nhan: 'Phụ cấp vị trí', khoa: 'position_allowance', nhom: 'thu' },
  { nhan: 'Bảo hiểm người lao động đóng', khoa: 'employee_insurance', nhom: 'tru' },
  { nhan: 'Đoàn phí người lao động đóng', khoa: 'employee_union', nhom: 'tru' },
  { nhan: 'Thuế thu nhập cá nhân khấu trừ', khoa: 'pit_withheld', nhom: 'tru' },
  { nhan: 'Bảo hiểm đơn vị đóng', khoa: 'employer_insurance', nhom: 'don_vi' },
  { nhan: 'Kinh phí công đoàn đơn vị đóng', khoa: 'employer_union', nhom: 'don_vi' },
]

/**
 * Bảng lương hiện ngay khi nhân sự đang gõ ở mục Lương.
 *
 * Bố cục theo tờ phụ lục lương để đối chiếu được với bản in. Số liệu do
 * máy chủ tính, không tính lại ở trình duyệt, nên không có công thức thứ
 * hai chạy song song với bản in ra PDF.
 */
export default function SalaryTable({ form }: { form: ContractForm }) {
  const [ketQua, setKetQua] = useState<Calculation | null>(null)
  const [loi, setLoi] = useState<string | null>(null)
  const [dangTinh, setDangTinh] = useState(false)
  const huy = useRef<AbortController | null>(null)

  const { job, compensation } = form
  const duDieuKien =
    job.position_id !== '' &&
    compensation.salary_amount !== '' &&
    compensation.insurance_base !== ''

  // Gộp thành chuỗi để chỉ tính lại khi số thật sự đổi.
  const dauVao = JSON.stringify([job.position_id, compensation])

  useEffect(() => {
    if (!duDieuKien) {
      setKetQua(null)
      setLoi(null)
      return
    }
    const hen = setTimeout(() => {
      huy.current?.abort()
      const bo = new AbortController()
      huy.current = bo
      setDangTinh(true)
      calcSalary(job.position_id, compensation, bo.signal)
        .then((r) => {
          setKetQua(r.calculation)
          setLoi(null)
        })
        .catch((e) => {
          if (e instanceof DOMException && e.name === 'AbortError') return
          if (e instanceof UnauthorizedError) return
          setKetQua(null)
          setLoi(e instanceof ApiError ? e.message : 'Không gọi được máy chủ')
        })
        .finally(() => setDangTinh(false))
    }, CHO_MS)
    return () => clearTimeout(hen)
    // dauVao gói đủ các giá trị cần theo dõi.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dauVao, duDieuKien])

  if (!duDieuKien) {
    return (
      <p className="hint">
        Chọn vị trí và nhập số tiền lương để bảng lương hiện ra.
      </p>
    )
  }

  if (loi) {
    return <p className="alert error">{loi}</p>
  }

  if (!ketQua) {
    return <p className="hint">Đang tính…</p>
  }

  const thu = DONG.filter((d) => d.nhom === 'thu')
  const tru = DONG.filter((d) => d.nhom === 'tru')
  const donVi = DONG.filter((d) => d.nhom === 'don_vi')

  return (
    <div className={dangTinh ? 'phu-luc dang-tinh' : 'phu-luc'}>
      <h3>Phụ lục lương (xem trước)</h3>

      <table className="calc">
        <tbody>
          {thu.map((d) => (
            <tr key={d.khoa}>
              <th>{d.nhan}</th>
              <td>{formatMoney(ketQua[d.khoa])} đ</td>
            </tr>
          ))}
          <tr className="tong">
            <th>Tổng thu nhập (Gross)</th>
            <td>{formatMoney(ketQua.gross_income)} đ</td>
          </tr>

          {tru.map((d) => (
            <tr key={d.khoa}>
              <th>{d.nhan}</th>
              <td>− {formatMoney(ketQua[d.khoa])} đ</td>
            </tr>
          ))}
          <tr className="highlight">
            <th>Thực nhận (Net)</th>
            <td>{formatMoney(ketQua.net_income)} đ</td>
          </tr>

          {donVi.map((d) => (
            <tr key={d.khoa} className="phu">
              <th>{d.nhan}</th>
              <td>{formatMoney(ketQua[d.khoa])} đ</td>
            </tr>
          ))}
          <tr className="phu tong">
            <th>Tổng chi phí của đơn vị</th>
            <td>{formatMoney(ketQua.employer_total_cost)} đ</td>
          </tr>
        </tbody>
      </table>

      <p className="hint">
        Các khoản đơn vị đóng không trừ vào thực nhận. Tỷ lệ khấu trừ hiện là
        chính sách minh họa, chưa được kế toán xác nhận.
      </p>
    </div>
  )
}
