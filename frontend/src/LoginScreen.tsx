import { useState, type FormEvent } from 'react'
import { ApiError, login } from './api'
import type { Account } from './types'

export default function LoginScreen({
  onLoggedIn,
}: {
  onLoggedIn: (account: Account) => void
}) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      onLoggedIn(await login(username, password))
    } catch (problem) {
      setError(
        problem instanceof ApiError ? problem.message : 'Không gọi được máy chủ',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page login-page">
      <form className="card login-card" onSubmit={submit}>
        <h1>Đăng nhập</h1>
        <p className="hint">
          Hệ thống tạo hợp đồng lao động cho 4 cơ sở. Chỉ tài khoản được cấp
          mới sử dụng được.
        </p>

        <label className="field">
          <span className="label">Tài khoản</span>
          <input
            autoFocus
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>

        <label className="field">
          <span className="label">Mật khẩu</span>
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>

        {error && <p className="alert error">{error}</p>}

        <button
          type="submit"
          className="primary"
          disabled={busy || !username.trim() || !password}
        >
          {busy ? 'Đang kiểm tra…' : 'Đăng nhập'}
        </button>

        <p className="hint">
          Quên mật khẩu thì nhờ người quản trị đặt lại bằng lệnh{' '}
          <code>python -m app.usertool doi-mat-khau &lt;tài khoản&gt;</code>.
        </p>
      </form>
    </div>
  )
}
