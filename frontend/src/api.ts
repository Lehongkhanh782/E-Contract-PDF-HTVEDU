import type {
  Account,
  ContractForm,
  OcrResult,
  OcrStatus,
  Position,
  PreviewResponse,
  Unit,
} from './types'

/** Lỗi có kèm thông điệp tiếng Việt do backend trả về. */
export class ApiError extends Error {}

/** Chưa đăng nhập hoặc phiên đã hết hạn. */
export class UnauthorizedError extends ApiError {}

// Luôn gửi kèm cookie phiên, kể cả khi frontend và backend khác cổng.
const WITH_SESSION: RequestInit = { credentials: 'include' }

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') return body.detail
    if (Array.isArray(body?.detail)) {
      // Lỗi 422 của Pydantic: gom tên trường cho dễ tìm.
      return body.detail
        .map((item: { loc?: unknown[]; msg?: string }) => {
          const field = (item.loc ?? []).filter((p) => p !== 'body').join('.')
          return field ? `${field}: ${item.msg}` : item.msg
        })
        .join('; ')
    }
  } catch {
    /* phần thân không phải JSON */
  }
  return `Máy chủ trả lỗi ${response.status}`
}

function fail(response: Response, message: string): never {
  if (response.status === 401) throw new UnauthorizedError(message)
  throw new ApiError(message)
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, WITH_SESSION)
  if (!response.ok) fail(response, await readError(response))
  return response.json() as Promise<T>
}

export function fetchMe() {
  return getJson<Account>('/api/me')
}

export function fetchOcrStatus() {
  return getJson<OcrStatus>('/api/ocr/status')
}

/** Gửi ảnh giấy tờ lên để máy đọc thử. Kết quả chỉ là gợi ý. */
export async function readIdCard(file: File): Promise<OcrResult> {
  const form = new FormData()
  form.append('anh', file)
  const response = await fetch('/api/ocr', {
    ...WITH_SESSION,
    method: 'POST',
    body: form,
  })
  if (!response.ok) fail(response, await readError(response))
  return response.json()
}

export async function login(
  username: string,
  password: string,
): Promise<Account> {
  const response = await fetch('/api/login', {
    ...WITH_SESSION,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!response.ok) throw new ApiError(await readError(response))
  return response.json()
}

export async function logout(): Promise<void> {
  await fetch('/api/logout', { ...WITH_SESSION, method: 'POST' })
}

export function fetchUnits() {
  return getJson<{ units: Unit[]; notice: string }>('/api/units')
}

export function fetchPositions() {
  return getJson<{ positions: Position[]; deduction_policy_status: string }>(
    '/api/positions',
  )
}

export async function preview(form: ContractForm): Promise<PreviewResponse> {
  const response = await fetch('/api/preview', {
    ...WITH_SESSION,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(form),
  })
  if (!response.ok) fail(response, await readError(response))
  return response.json()
}

/** Tải PDF về máy. Trả tên file đã lưu. */
export async function downloadPdf(form: ContractForm): Promise<string> {
  const response = await fetch('/api/generate', {
    ...WITH_SESSION,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(form),
  })
  if (!response.ok) fail(response, await readError(response))

  const disposition = response.headers.get('Content-Disposition') ?? ''
  const matched = /filename="?([^"]+)"?/.exec(disposition)
  const name = matched?.[1] ?? 'Bo_hop_dong_thu_nghiem.pdf'

  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
  return name
}
