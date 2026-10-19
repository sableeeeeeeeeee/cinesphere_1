import { useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import api, { errInfo } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { ErrorBox, Field } from '../components/ui'
import { Logo } from '../components/Navbar'
import { useToast } from '../context/ToastContext'

function Shell({ title, children }) {
  return (
    <div className="mx-auto max-w-md pt-6">
      <div className="mb-6 flex justify-center"><Logo /></div>
      <div className="card space-y-4"><h1 className="text-xl font-bold">{title}</h1>{children}</div>
    </div>
  )
}

export function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [f, setF] = useState({ email: '', password: '' })
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr('')
    try { const u = await login(f.email, f.password); nav(loc.state?.from || (u.role === 'admin' ? '/admin' : '/'), { replace: true }) }
    catch (x) { setErr(errInfo(x).message) } finally { setBusy(false) }
  }
  return (
    <Shell title="Sign in">
      <form onSubmit={submit} className="space-y-4">
        <ErrorBox>{err}</ErrorBox>
        <Field label="Email"><input className="input" type="email" required autoComplete="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
        <Field label="Password"><input className="input" type="password" required autoComplete="current-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
        <button className="btn-primary w-full" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
      </form>
      <div className="flex justify-between text-sm text-slate-400"><Link to="/forgot" className="hover:text-white">Forgot password?</Link><Link to="/register" className="text-brand-soft">Create account</Link></div>
    </Shell>
  )
}

export function Register() {
  const { register } = useAuth()
  const nav = useNavigate()
  const [f, setF] = useState({ name: '', email: '', phone: '', password: '' })
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr('')
    try { await register({ ...f, phone: f.phone || null }); nav('/', { replace: true }) } catch (x) { setErr(errInfo(x).message) } finally { setBusy(false) }
  }
  const s = (k) => ({ value: f[k], onChange: (e) => setF({ ...f, [k]: e.target.value }) })
  return (
    <Shell title="Create your account">
      <form onSubmit={submit} className="space-y-4">
        <ErrorBox>{err}</ErrorBox>
        <Field label="Full name"><input className="input" required minLength={2} {...s('name')} /></Field>
        <Field label="Email"><input className="input" type="email" required {...s('email')} /></Field>
        <Field label="Phone (optional)"><input className="input" type="tel" {...s('phone')} /></Field>
        <Field label="Password (min 8 characters)"><input className="input" type="password" required minLength={8} autoComplete="new-password" {...s('password')} /></Field>
        <button className="btn-primary w-full" disabled={busy}>{busy ? 'Creating…' : 'Create account'}</button>
      </form>
      <p className="text-sm text-slate-400">Already registered? <Link to="/login" className="text-brand-soft">Sign in</Link></p>
    </Shell>
  )
}

export function Forgot() {
  const [email, setEmail] = useState('')
  const [res, setRes] = useState(null)
  const [err, setErr] = useState('')
  const submit = async (e) => { e.preventDefault(); setErr(''); try { setRes((await api.post('/auth/forgot-password', { email })).data) } catch (x) { setErr(errInfo(x).message) } }
  return (
    <Shell title="Reset your password">
      <form onSubmit={submit} className="space-y-4">
        <ErrorBox>{err}</ErrorBox>
        <Field label="Email"><input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
        <button className="btn-primary w-full">Send reset link</button>
      </form>
      {res && <div className="rounded-xl bg-panel p-3 text-sm text-slate-300">{res.message}
        {res.dev_reset_token && <div className="mt-2">Development mode (no email server): <Link className="text-brand-soft underline" to={`/reset?token=${res.dev_reset_token}`}>open the reset page</Link></div>}</div>}
    </Shell>
  )
}

export function Reset() {
  const [p] = useSearchParams()
  const nav = useNavigate()
  const toast = useToast()
  const [pw, setPw] = useState('')
  const [err, setErr] = useState('')
  const submit = async (e) => {
    e.preventDefault(); setErr('')
    try { await api.post('/auth/reset-password', { token: p.get('token'), new_password: pw }); toast('Password updated. Please sign in.'); nav('/login') } catch (x) { setErr(errInfo(x).message) }
  }
  return (
    <Shell title="Choose a new password">
      <form onSubmit={submit} className="space-y-4">
        <ErrorBox>{err}</ErrorBox>
        <Field label="New password"><input className="input" type="password" required minLength={8} value={pw} onChange={(e) => setPw(e.target.value)} /></Field>
        <button className="btn-primary w-full">Update password</button>
      </form>
    </Shell>
  )
}
