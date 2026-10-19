import { useCallback, useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import api, { errInfo } from '../../services/api'
import { ErrorBox, Spinner } from '../../components/ui'
import { useAuth } from '../../context/AuthContext'
import { money, localDateStr, tzOffset } from '../../utils/format'

const Card = ({ label, value, sub }) => <div className="card"><div className="label">{label}</div><div className="text-2xl font-bold">{value}</div>{sub && <div className="text-xs text-slate-500">{sub}</div>}</div>
const tip = { contentStyle: { background: '#12142a', border: '1px solid #262a4a', borderRadius: 12 } }

export default function Dashboard() {
  const { user } = useAuth()
  const today = new Date(); const ago = new Date(); ago.setDate(ago.getDate() - 29)
  const [f, setF] = useState({ date_from: localDateStr(ago), date_to: localDateStr(today), cinema_id: '', movie_id: '' })
  const [s, setS] = useState(null)
  const [cinemas, setCinemas] = useState([])
  const [movies, setMovies] = useState([])
  const [err, setErr] = useState('')
  useEffect(() => { if (user.role === 'admin') { api.get('/admin/cinemas').then((r) => setCinemas(r.data)); api.get('/admin/movies').then((r) => setMovies(r.data)) } }, [user])
  const [updated, setUpdated] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  // Always asks the server, which sums real booking rows. Refreshes by itself every 15 s and on filter change.
  const load = useCallback(() => {
    setRefreshing(true)
    return api.get('/admin/stats', { params: { ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)), tz: tzOffset() } })
      .then((r) => { setS(r.data); setErr(''); setUpdated(new Date()) }).catch((e) => setErr(errInfo(e).message)).finally(() => setRefreshing(false))
  }, [f])
  useEffect(() => {
    if (user.role !== 'admin') return
    load()
    const t = setInterval(load, 15000)
    const onVis = () => document.visibilityState === 'visible' && load()
    document.addEventListener('visibilitychange', onVis)
    return () => { clearInterval(t); document.removeEventListener('visibilitychange', onVis) }
  }, [load, user])
  if (user.role !== 'admin') return <div className="card">Welcome. Use <b>Validate ticket</b> and <b>Food</b> in the sidebar.</div>
  if (err) return <ErrorBox>{err}</ErrorBox>
  if (!s) return <Spinner />
  const c = s.cards
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-3"><div className="mr-auto"><h1 className="text-2xl font-bold">Dashboard</h1><p className="text-xs text-slate-500">Live from the database{updated ? ` \u2022 updated ${updated.toLocaleTimeString()}` : ''}</p></div>
        <button className="btn-ghost" onClick={load} disabled={refreshing} aria-label="Refresh now"><RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />Refresh</button>
        <input type="date" className="input !w-auto" aria-label="From" value={f.date_from} onChange={(e) => setF({ ...f, date_from: e.target.value })} />
        <input type="date" className="input !w-auto" aria-label="To" value={f.date_to} onChange={(e) => setF({ ...f, date_to: e.target.value })} />
        <select className="input !w-auto" aria-label="Cinema" value={f.cinema_id} onChange={(e) => setF({ ...f, cinema_id: e.target.value })}><option value="">All cinemas</option>{cinemas.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select>
        <select className="input !w-auto" aria-label="Movie" value={f.movie_id} onChange={(e) => setF({ ...f, movie_id: e.target.value })}><option value="">All movies</option>{movies.map((x) => <option key={x.id} value={x.id}>{x.title}</option>)}</select></div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card label="Confirmed revenue" value={money(c.confirmed_revenue)} sub={`${c.confirmed_bookings} confirmed bookings`} />
        <Card label="Gross booked value" value={money(c.gross_bookings_value)} sub={`${c.bookings_total} bookings incl. cancelled`} />
        <Card label="Refunds" value={money(c.refunds)} sub={`${c.cancelled_bookings} cancelled`} />
        <Card label="Tickets sold" value={c.tickets_sold} />
        <Card label="Active movies" value={c.active_movies} /><Card label="Customers" value={c.customers} />
        <Card label="Upcoming shows" value={c.upcoming_shows} sub={`${c.occupancy_percent}% occupancy (next shows)`} />
        <Card label="Food orders" value={c.food_orders} sub={`${money(c.food_sales)} sales`} />
        <Card label="Pending review reports" value={c.pending_reports} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Chart title="Daily confirmed revenue (₹)"><LineChart data={s.daily.map((d) => ({ ...d, revenue: d.revenue / 100 }))}><CartesianGrid stroke="#262a4a" /><XAxis dataKey="date" stroke="#94a3b8" fontSize={11} /><YAxis stroke="#94a3b8" fontSize={11} /><Tooltip {...tip} /><Line dataKey="revenue" stroke="#fb7185" strokeWidth={2} dot={false} /></LineChart></Chart>
        <Chart title="Bookings per day"><BarChart data={s.daily}><CartesianGrid stroke="#262a4a" /><XAxis dataKey="date" stroke="#94a3b8" fontSize={11} /><YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} /><Tooltip {...tip} /><Bar dataKey="bookings" fill="#7c3aed" radius={4} /></BarChart></Chart>
        <Chart title="Most popular movies (tickets)"><BarChart data={s.popular_movies} layout="vertical"><CartesianGrid stroke="#262a4a" /><XAxis type="number" stroke="#94a3b8" fontSize={11} allowDecimals={false} /><YAxis type="category" dataKey="title" width={110} stroke="#94a3b8" fontSize={11} /><Tooltip {...tip} /><Bar dataKey="tickets" fill="#e11d48" radius={4} /></BarChart></Chart>
        <Chart title="Revenue by cinema (₹)"><BarChart data={s.revenue_by_cinema.map((d) => ({ ...d, revenue: d.revenue / 100 }))}><CartesianGrid stroke="#262a4a" /><XAxis dataKey="cinema" stroke="#94a3b8" fontSize={11} /><YAxis stroke="#94a3b8" fontSize={11} /><Tooltip {...tip} /><Bar dataKey="revenue" fill="#38bdf8" radius={4} /></BarChart></Chart>
        <Chart title="Seat occupancy: upcoming shows"><BarChart data={s.occupancy}><CartesianGrid stroke="#262a4a" /><XAxis dataKey="label" stroke="#94a3b8" fontSize={10} /><YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} /><Tooltip {...tip} /><Bar dataKey="sold" fill="#34d399" radius={4} /><Bar dataKey="capacity" fill="#334155" radius={4} /></BarChart></Chart>
      </div>
    </div>
  )
}
const Chart = ({ title, children }) => <div className="card"><h3 className="mb-3 text-sm font-semibold">{title}</h3><div className="h-64"><ResponsiveContainer>{children}</ResponsiveContainer></div></div>
