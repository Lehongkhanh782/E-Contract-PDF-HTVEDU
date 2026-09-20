import type {
  Account,
  ContractForm,
  ProbationForm,
  EmployeeList,
  OcrResult,
  OcrStatus,
  Position,
  PreviewResponse,
  PrincipalList,
  SalaryResponse,
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

/** Danh sách nhân viên từ Google Sheet dùng chung, nếu đã nối. */
export function fetchEmployees() {
  return getJson<EmployeeList>('/api/employees')
}

/** Hiệu trưởng từng cơ sở; trả về rỗng nếu chưa nối Sheet. */
export function fetchPrincipals() {
  return getJson<PrincipalList>('/api/principals')
}

export function fetchOcrStatus() {
  return getJson<OcrStatus>('/api/ocr/status')
}

/** Gửi một đến ba tệp giấy tờ lên để máy đọc. Kết quả chỉ là gợi ý. */
export async function readIdCard(files: File[]): Promise<OcrResult> {
  const form = new FormData()
  for (const file of files) form.append('anh', file)
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

/** Tính lương ngay khi đang gõ; chỉ cần vị trí và khối lương. */
export async function calcSalary(
  positionId: string,
  compensation: ContractForm['compensation'],
  signal?: AbortSignal,
): Promise<SalaryResponse> {
  const response = await fetch('/api/salary', {
    ...WITH_SESSION,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ position_id: positionId, compensation }),
    signal,
  })
  if (!response.ok) fail(response, await readError(response))
  return response.json()
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
export async function downloadProbationPdf(
  form: ProbationForm,
): Promise<string> {
  return taiPdf('/api/generate/probation', form, 'Hop_dong_thu_viec.pdf')
}

export async function downloadPdf(form: ContractForm): Promise<string> {
  return taiPdf('/api/generate', form, 'Bo_hop_dong.pdf')
}

/** Gửi biểu mẫu, nhận PDF và bảo trình duyệt tải xuống. */
async function taiPdf(
  duong_dan: string,
  form: unknown,
  ten_du_phong: string,
): Promise<string> {
  const response = await fetch(duong_dan, {
    ...WITH_SESSION,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(form),
  })
  if (!response.ok) fail(response, await readError(response))

  const disposition = response.headers.get('Content-Disposition') ?? ''
  const matched = /filename="?([^"]+)"?/.exec(disposition)
  const name = matched?.[1] ?? ten_du_phong

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
