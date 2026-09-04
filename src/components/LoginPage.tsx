import { FormEvent, useState } from 'react'

export function LoginPage({ onLogin }: { onLogin: (username: string, password: string) => Promise<void> }) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await onLogin(username, password)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '登录失败')
    } finally {
      setBusy(false)
    }
  }

  return <main className="login-page"><section className="login-card">
    <div className="seal login-seal" aria-hidden="true">谱</div>
    <p className="eyebrow">GUIYUAN · PRIVATE ARCHIVE</p><h1>管理员登录</h1>
    <p>家族资料默认私密，仅管理员可以查看和维护。</p>
    <form onSubmit={submit}>
      <label>管理员账号<input aria-label="管理员账号" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" /></label>
      <label>密码<input aria-label="密码" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="confirm-button" disabled={busy}>{busy ? '正在验证…' : '登录归源'}</button>
    </form>
  </section></main>
}
