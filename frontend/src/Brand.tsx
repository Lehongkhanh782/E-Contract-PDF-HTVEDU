import logoDay from './assets/logo.png'
import logoMark from './assets/logo-mark.png'

export const TEN_TO_CHUC = 'HTV EDU Group'
export const TEN_HE_THONG = 'Hệ thống hợp đồng lao động'

/**
 * Khối thương hiệu dùng chung.
 *
 * Bản đầy đủ có chữ HTV EDU Group nằm trong ảnh nên không lặp lại bằng
 * chữ; bản rút gọn chỉ lấy ngọn lửa nên cần ghi tên bên cạnh.
 */
export default function Brand({ full = false }: { full?: boolean }) {
  return (
    <div className="brand">
      <img src={full ? logoDay : logoMark} alt={`Logo ${TEN_TO_CHUC}`} />
      <div className="brand-text">
        {!full && <p className="brand-name">{TEN_TO_CHUC}</p>}
        <h1>{TEN_HE_THONG}</h1>
      </div>
    </div>
  )
}
