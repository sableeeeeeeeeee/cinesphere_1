import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { BadgeCheck, Clock, Flag, Star, ThumbsUp, Trash2 } from 'lucide-react'
import api, { errInfo } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { Empty, ErrorBox, Spinner, Stars } from '../components/ui'
import MovieCard from '../components/MovieCard'
import { fmtTime, localDateStr, money, tzOffset } from '../utils/format'
import { pushRecent, useCity } from '../hooks/useCity'

export default function MovieDetail() {
  const { id } = useParams()
  const [movie, setMovie] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    setMovie(null)
    api.get(`/movies/${id}`).then((r) => { setMovie(r.data); pushRecent(Number(id)) }).catch((e) => setError(errInfo(e).message))
  }, [id])
  if (error) return <ErrorBox>{error}</ErrorBox>
  if (!movie) return <Spinner />
  return (
    <div className="space-y-10">
      <section className="relative overflow-hidden rounded-2xl border border-edge">
        <img src={movie.backdrop_url} alt="" className="absolute inset-0 h-full w-full object-cover opacity-30" />
        <div className="absolute inset-0 bg-gradient-to-t from-ink via-ink/70 to-ink/30" />
        <div className="relative flex flex-col gap-6 p-6 sm:flex-row sm:p-10">
          <img src={movie.poster_url} alt={`${movie.title} poster`} className="w-44 rounded-2xl border border-edge shadow-2xl sm:w-56" />
          <div className="space-y-3">
            <h1 className="font-display text-4xl font-bold tracking-tight sm:text-5xl">{movie.title}</h1>
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="flex items-center gap-2 text-slate-200"><Stars value={movie.avg_rating} /> {movie.rating_count ? `${movie.avg_rating} (${movie.rating_count})` : 'No ratings yet'}</span>
              <span className="chip">{movie.certificate}</span><span className="chip"><Clock size={12} className="mr-1 inline" />{movie.duration_min} min</span>
              <span className="chip">{movie.language}</span>{movie.genres.map((g) => <span key={g} className="chip">{g}</span>)}
            </div>
            <p className="max-w-2xl text-slate-300">{movie.synopsis}</p>
            <p className="text-sm text-slate-400"><b className="text-slate-200">Director:</b> {movie.director || '—'} &nbsp; <b className="text-slate-200">Cast:</b> {movie.cast.join(', ') || '—'}</p>
            <p className="text-sm text-slate-400"><b className="text-slate-200">Release:</b> {movie.release_date || 'TBA'}</p>
            <a href="#shows" className="btn-primary mt-2 inline-flex">Book tickets</a>
          </div>
        </div>
      </section>

      {movie.trailer_url && (
        <section className="space-y-3"><h2 className="text-xl font-bold">Trailer</h2>
          <div className="aspect-video max-w-3xl overflow-hidden rounded-2xl border border-edge">
            <iframe className="h-full w-full" src={movie.trailer_url} title={`${movie.title} trailer`} allow="accelerometer; encrypted-media; picture-in-picture" allowFullScreen loading="lazy" />
          </div>
        </section>
      )}
      <Showtimes movieId={movie.id} />
      <Reviews movieId={movie.id} onChange={() => api.get(`/movies/${id}`).then((r) => setMovie(r.data))} />
      {movie.similar.length > 0 && (
        <section className="space-y-3"><h2 className="text-xl font-bold">You might also like</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-6">{movie.similar.map((m) => <MovieCard key={m.id} movie={m} />)}</div></section>
      )}
    </div>
  )
}

function Showtimes({ movieId }) {
  const nav = useNavigate()
  const [city, setCity] = useCity()
  const [cities, setCities] = useState([])
  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => { const d = new Date(); d.setDate(d.getDate() + i); return d }), [])
  const [day, setDay] = useState(localDateStr(days[0]))
  const [shows, setShows] = useState(null)
  useEffect(() => { api.get('/cities').then((r) => { setCities(r.data); if (!city && r.data[0]) setCity(r.data[0]) }) }, []) // eslint-disable-line
  useEffect(() => {
    setShows(null)
    api.get('/shows', { params: { movie_id: movieId, city: city || undefined, date: day, tz: tzOffset() } }).then((r) => setShows(r.data))
  }, [movieId, city, day])
  const byCinema = (shows || []).reduce((a, s) => ((a[s.cinema_name] ||= []).push(s), a), {})
  return (
    <section id="shows" className="space-y-4 scroll-mt-24">
      <div className="flex flex-wrap items-center gap-3"><h2 className="text-xl font-bold">Showtimes</h2>
        <select className="input !w-auto" aria-label="City" value={city} onChange={(e) => setCity(e.target.value)}>{cities.map((c) => <option key={c}>{c}</option>)}</select></div>
      <div className="flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Date">
        {days.map((d) => { const v = localDateStr(d); return (
          <button key={v} role="tab" aria-selected={day === v} onClick={() => setDay(v)} className={`min-w-16 rounded-xl border px-3 py-2 text-center text-sm ${day === v ? 'border-brand bg-brand text-white' : 'border-edge text-slate-300'}`}>
            <div className="text-xs opacity-80">{d.toLocaleDateString([], { weekday: 'short' })}</div><div className="font-bold">{d.getDate()}</div></button>) })}
      </div>
      {!shows ? <Spinner /> : shows.length === 0 ? <Empty>No shows on this date in {city || 'this city'}.</Empty> : Object.entries(byCinema).map(([name, list]) => (
        <div key={name} className="card space-y-3">
          <div><h3 className="font-semibold">{name}</h3><p className="text-xs text-slate-400">{list[0].city}</p></div>
          <div className="flex flex-wrap gap-3">
            {list.map((s) => (
              <button key={s.id} disabled={s.available_seats === 0} onClick={() => nav(`/shows/${s.id}/seats`)} className="rounded-xl border border-emerald-700/60 px-4 py-2 text-left hover:bg-emerald-900/30 disabled:cursor-not-allowed disabled:border-edge disabled:opacity-50">
                <div className="font-bold text-emerald-300">{fmtTime(s.starts_at)}</div>
                <div className="text-[11px] text-slate-400">{s.format} • {s.screen_name}</div>
                <div className="text-[11px] text-slate-400">{s.available_seats === 0 ? 'Sold out' : `${s.available_seats} seats • from ${money(Math.min(...Object.values(s.prices)))}`}</div>
              </button>))}
          </div>
        </div>))}
    </section>
  )
}

function Reviews({ movieId, onChange }) {
  const { user } = useAuth()
  const toast = useToast()
  const [sort, setSort] = useState('newest')
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [form, setForm] = useState({ rating: 5, text: '' })
  const [editing, setEditing] = useState(null)
  const load = () => api.get(`/movies/${movieId}/reviews`, { params: { sort, page } }).then((r) => setData(r.data))
  useEffect(() => { load() }, [movieId, sort, page]) // eslint-disable-line
  const mine = data?.items.find((r) => r.is_mine)

  const submit = async (e) => {
    e.preventDefault()
    try {
      if (editing) await api.patch(`/reviews/${editing}`, form); else await api.post(`/movies/${movieId}/reviews`, form)
      toast(editing ? 'Review updated' : 'Review posted'); setEditing(null); setForm({ rating: 5, text: '' }); await load(); onChange()
    } catch (x) { toast(errInfo(x).message, 'error') }
  }
  const act = async (fn, msg) => { try { await fn(); msg && toast(msg); await load(); onChange() } catch (x) { toast(errInfo(x).message, 'error') } }
  const total = data?.total || 0

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-bold">Ratings &amp; reviews</h2>
      {data && (
        <div className="card flex flex-wrap gap-8">
          <div><div className="text-5xl font-bold">{data.avg_rating || '–'}</div><Stars value={data.avg_rating} /><div className="text-xs text-slate-400">{total} ratings</div></div>
          <div className="min-w-60 flex-1 space-y-1">{[5, 4, 3, 2, 1].map((n) => (
            <div key={n} className="flex items-center gap-2 text-xs"><span className="w-3">{n}</span><div className="h-2 flex-1 rounded bg-ink"><div className="h-2 rounded bg-amber-400" style={{ width: `${total ? (data.distribution[n] / total) * 100 : 0}%` }} /></div><span className="w-6 text-right text-slate-400">{data.distribution[n]}</span></div>))}</div>
        </div>
      )}
      {user ? (!mine || editing) && (
        <form onSubmit={submit} className="card space-y-3">
          <div className="flex items-center gap-2" role="radiogroup" aria-label="Rating">{[1, 2, 3, 4, 5].map((n) => (
            <button type="button" key={n} role="radio" aria-checked={form.rating === n} aria-label={`${n} stars`} onClick={() => setForm({ ...form, rating: n })} className={n <= form.rating ? 'text-amber-400' : 'text-slate-600'}><Star size={26} fill={n <= form.rating ? 'currentColor' : 'none'} /></button>))}</div>
          <textarea className="input" rows={3} maxLength={2000} placeholder="Share your thoughts (optional)" value={form.text} onChange={(e) => setForm({ ...form, text: e.target.value })} />
          <button className="btn-primary">{editing ? 'Save changes' : 'Post review'}</button>
        </form>
      ) : <p className="text-sm text-slate-400"><Link to="/login" className="text-brand-soft">Sign in</Link> to rate this movie.</p>}
      <div className="flex gap-2 text-sm">{[['newest', 'Newest'], ['highest', 'Highest rated'], ['helpful', 'Most helpful']].map(([v, l]) => (
        <button key={v} onClick={() => { setSort(v); setPage(1) }} className={`chip ${sort === v ? 'border-brand text-white' : ''}`}>{l}</button>))}</div>
      {data?.items.length === 0 && <Empty>No reviews yet. Be the first!</Empty>}
      {data?.items.map((r) => (
        <article key={r.id} className="card space-y-2">
          <div className="flex flex-wrap items-center gap-2"><b>{r.user_name}</b><Stars value={r.rating} />
            {r.verified_booking && <span className="flex items-center gap-1 rounded-full bg-emerald-900/50 px-2 py-0.5 text-xs text-emerald-300"><BadgeCheck size={12} />Verified booking</span>}
            <span className="ml-auto text-xs text-slate-500">{new Date(r.created_at).toLocaleDateString()}</span></div>
          {r.text && <p className="text-sm text-slate-300">{r.text}</p>}
          <div className="flex items-center gap-3 text-xs text-slate-400">
            {!r.is_mine && <button className="flex items-center gap-1 hover:text-white" onClick={() => act(() => api.post(`/reviews/${r.id}/helpful`))} aria-label="Mark helpful"><ThumbsUp size={14} />Helpful ({r.helpful_count})</button>}
            {r.is_mine && <><button className="hover:text-white" onClick={() => { setEditing(r.id); setForm({ rating: r.rating, text: r.text }) }}>Edit</button>
              <button className="flex items-center gap-1 hover:text-red-300" onClick={() => window.confirm('Delete your review?') && act(() => api.delete(`/reviews/${r.id}`), 'Review deleted')}><Trash2 size={14} />Delete</button></>}
            {!r.is_mine && user && <button className="flex items-center gap-1 hover:text-red-300" onClick={() => { const reason = window.prompt('Why are you reporting this review?'); reason && act(() => api.post(`/reviews/${r.id}/report`, { reason }), 'Report sent to moderators') }}><Flag size={14} />Report</button>}
          </div>
        </article>))}
      {total > 10 && <div className="flex justify-center gap-3"><button className="btn-ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button><button className="btn-ghost" disabled={page * 10 >= total} onClick={() => setPage(page + 1)}>Next</button></div>}
    </section>
  )
}
