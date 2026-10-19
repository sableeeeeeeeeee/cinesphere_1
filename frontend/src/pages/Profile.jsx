import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api, { errInfo } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { ErrorBox, Field } from '../components/ui'
import MovieCard from '../components/MovieCard'

export default function Profile() {
  const { user, setUser } = useAuth()
  const toast = useToast()
  const [f, setF] = useState({ name: user.name, phone: user.phone || '' })
  const [pw, setPw] = useState({ current_password: '', new_password: '' })
  const [err, setErr] = useState('')
  const [watch, setWatch] = useState([])
  useEffect(() => { api.get('/watchlist').then((r) => setWatch(r.data)) }, [])
  const save = async (e) => { e.preventDefault(); try { const r = await api.patch('/auth/me', { name: f.name, phone: f.phone || null }); setUser(r.data); toast('Profile updated') } catch (x) { toast(errInfo(x).message, 'error') } }
  const change = async (e) => { e.preventDefault(); setErr(''); try { await api.post('/auth/change-password', pw); toast('Password changed'); setPw({ current_password: '', new_password: '' }) } catch (x) { setErr(errInfo(x).message) } }
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold">My profile</h1>
      <form onSubmit={save} className="card grid gap-4 sm:grid-cols-2">
        <Field label="Name"><input className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field label="Phone"><input className="input" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} /></Field>
        <Field label="Email"><input className="input opacity-60" value={user.email} disabled /></Field>
        <div className="flex items-end"><button className="btn-primary">Save profile</button></div>
      </form>
      <form onSubmit={change} className="card grid gap-4 sm:grid-cols-2"><div className="sm:col-span-2"><ErrorBox>{err}</ErrorBox></div>
        <Field label="Current password"><input className="input" type="password" required value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} /></Field>
        <Field label="New password"><input className="input" type="password" required minLength={8} value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></Field>
        <button className="btn-ghost w-fit">Change password</button></form>
      <section className="space-y-3"><h2 className="font-bold">Watchlist</h2>
        {watch.length === 0 ? <p className="text-sm text-slate-400">Tap the heart on a movie to save it. <Link to="/" className="text-brand-soft">Browse movies</Link></p> : <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">{watch.map((m) => <MovieCard key={m.id} movie={m} />)}</div>}</section>
    </div>
  )
}
