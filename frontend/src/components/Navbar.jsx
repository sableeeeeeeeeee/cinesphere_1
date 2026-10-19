import { useEffect, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { Bell, LogOut, Popcorn, Search, Shield, Ticket, User } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

export function Logo({ className = '' }) {
  return (
    <span className={`flex items-center gap-2.5 text-xl font-semibold tracking-tight ${className}`}>
      <svg width="30" height="30" viewBox="0 0 64 64" aria-hidden="true">
        <defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#e5484d" /><stop offset="1" stopColor="#7c5cff" /></linearGradient></defs>
        <circle cx="32" cy="32" r="22" fill="none" stroke="url(#lg)" strokeWidth="6" /><path d="M26 22l17 10-17 10z" fill="#fff" />
      </svg>
      <span>Cine<span className="text-brand-soft">Sphere</span></span>
    </span>
  )
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const [q, setQ] = useState('')
  const [unread, setUnread] = useState(0)
  const [open, setOpen] = useState(false)
  const [notes, setNotes] = useState([])

  useEffect(() => {
    if (!user) return
    api.get('/notifications').then((r) => { setNotes(r.data); setUnread(r.data.filter((n) => !n.is_read).length) }).catch(() => {})
  }, [user, open])

  const submit = (e) => { e.preventDefault(); nav(`/?q=${encodeURIComponent(q)}`) }
  const link = ({ isActive }) => `rounded-lg px-3 py-2 text-sm font-medium ${isActive ? 'text-white' : 'text-slate-400 hover:text-white'}`

  return (
    <header className="sticky top-0 z-30 border-b border-edge bg-ink/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3">
        <Link to="/" aria-label="CineSphere home"><Logo /></Link>
        <form onSubmit={submit} className="relative order-3 w-full sm:order-none sm:w-72" role="search">
          <Search size={16} className="absolute left-3 top-3 text-slate-500" />
          <input className="input pl-9" placeholder="Search movies" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search movies" />
        </form>
        <nav className="ml-auto flex items-center gap-1">
          <NavLink to="/food" className={link}><Popcorn size={16} className="mr-1 inline" />Food</NavLink>
          {user && <NavLink to="/bookings" className={link}><Ticket size={16} className="mr-1 inline" />My Bookings</NavLink>}
          {user && ['admin', 'staff'].includes(user.role) && <NavLink to="/admin" className={link}><Shield size={16} className="mr-1 inline" />Admin</NavLink>}
          {user ? (
            <>
              <div className="relative">
                <button className="btn-ghost relative !px-3" aria-label="Notifications" onClick={() => { setOpen(!open); if (!open && unread) api.post('/notifications/read-all').then(() => setUnread(0)) }}>
                  <Bell size={16} />{unread > 0 && <span className="absolute -right-1 -top-1 grid h-4 w-4 place-items-center rounded-full bg-brand text-[10px]">{unread}</span>}
                </button>
                {open && (
                  <div className="absolute right-0 mt-2 w-72 rounded-xl border border-edge bg-panel p-2 shadow-2xl">
                    {notes.length === 0 && <p className="p-3 text-sm text-slate-400">No notifications yet.</p>}
                    {notes.slice(0, 6).map((n) => <div key={n.id} className="rounded-lg p-2 text-sm hover:bg-ink"><b>{n.title}</b><div className="text-xs text-slate-400">{n.body}</div></div>)}
                  </div>
                )}
              </div>
              <Link to="/profile" className="btn-ghost !px-3" aria-label="Profile"><User size={16} /><span className="hidden sm:inline">{user.name.split(' ')[0]}</span></Link>
              <button className="btn-ghost !px-3" aria-label="Log out" onClick={async () => { await logout(); nav('/') }}><LogOut size={16} /></button>
            </>
          ) : <Link to="/login" className="btn-primary">Sign in</Link>}
        </nav>
      </div>
    </header>
  )
}
