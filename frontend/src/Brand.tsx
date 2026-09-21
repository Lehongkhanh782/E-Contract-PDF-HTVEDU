import logoDay from './assets/logo.png'
import logoMark from './assets/logo-mark.png'

export const TEN_TO_CHUC = 'HTV EDU Group'
export const TEN_HE_THONG = 'Hệ thống hợp đồng lao động'

/**
 * Số phiên bản hiện trên chân trang.
 *
 * Tăng số này mỗi khi có thay đổi người dùng nhìn thấy được, để biết máy
 * chủ đã chạy bản mới hay còn bản cũ trong bộ nhớ đệm trình duyệt.
 */
export const PHIEN_BAN = '2.3'
export const MO_TA_PHIEN_BAN = 'nhận cả địa chỉ viết liền'

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
