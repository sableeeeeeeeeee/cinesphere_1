import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Play, Tag } from 'lucide-react'
import api, { errInfo } from '../services/api'
import MovieCard from '../components/MovieCard'
import { Empty, ErrorBox, Spinner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useCity, getRecent } from '../hooks/useCity'
import { useToast } from '../context/ToastContext'

const LANGS = ['English', 'Hindi', 'Tamil']

export default function Home() {
  const [params, setParams] = useSearchParams()
  const { user } = useAuth()
  const toast = useToast()
  const [city, setCity] = useCity()
  const [cities, setCities] = useState([])
  const [genres, setGenres] = useState([])
  const [data, setData] = useState(null)
  const [hero, setHero] = useState(null)
  const [top, setTop] = useState([])
  const [recent, setRecent] = useState([])
  const [offers, setOffers] = useState([])
  const [saved, setSaved] = useState(new Set())
  const [error, setError] = useState('')
  const q = params.get('q') || ''
  const release = params.get('release') || 'now_showing'
  const language = params.get('language') || ''
  const genre = params.get('genre') || ''
  const sort = params.get('sort') || 'newest'
  const page = Number(params.get('page') || 1)
  const [qInput, setQInput] = useState(q)

  const set = (k, v) => { const p = new URLSearchParams(params); v ? p.set(k, v) : p.delete(k); if (k !== 'page') p.delete('page'); setParams(p) }

  useEffect(() => { // debounced search
    const t = setTimeout(() => qInput !== q && set('q', qInput), 350)
    return () => clearTimeout(t)
  }, [qInput]) // eslint-disable-line
  useEffect(() => setQInput(q), [q])

  useEffect(() => {
    api.get('/cities').then((r) => setCities(r.data))
    api.get('/genres').then((r) => setGenres(r.data))
    api.get('/movies', { params: { sort: 'trending', page_size: 6, release: 'now_showing' } }).then((r) => setHero(r.data.items[0]))
    api.get('/movies', { params: { sort: 'rating', page_size: 6 } }).then((r) => setTop(r.data.items))
    api.get('/offers').then((r) => setOffers(r.data))
    const ids = getRecent()
    Promise.all(ids.slice(0, 5).map((id) => api.get(`/movies/${id}`).then((r) => r.data).catch(() => null))).then((x) => setRecent(x.filter(Boolean)))
  }, [])
  useEffect(() => { if (user) api.get('/watchlist').then((r) => setSaved(new Set(r.data.map((m) => m.id)))) }, [user])

  useEffect(() => {
    setData(null)
    api.get('/movies', { params: { q: q || undefined, release, language: language || undefined, genre: genre || undefined, sort, page, page_size: 12 } })
      .then((r) => { setData(r.data); setError('') }).catch((e) => setError(errInfo(e).message))
  }, [q, release, language, genre, sort, page])

  const toggleWatch = async (id) => {
    if (!user) return toast('Sign in to save movies to your watchlist', 'error')
    const r = await api.post(`/watchlist/${id}`)
    setSaved((s) => { const n = new Set(s); r.data.saved ? n.add(id) : n.delete(id); return n })
  }
  const pages = data ? Math.ceil(data.total / data.page_size) : 0

  return (
    <div className="space-y-10">
      {hero && !q && (
        <section className="relative overflow-hidden rounded-2xl border border-edge">
          <img src={hero.backdrop_url} alt="" className="absolute inset-0 h-full w-full object-cover opacity-60" />
          <div className="absolute inset-0 bg-gradient-to-r from-ink via-ink/85 to-ink/10" />
          <div className="relative max-w-xl space-y-4 p-8 sm:p-14">
            <span className="chip border-brand text-brand-soft">Trending now</span>
            <h1 className="font-display text-4xl font-bold tracking-tight sm:text-6xl">{hero.title}</h1>
            <p className="line-clamp-3 text-slate-300">{hero.synopsis}</p>
            <div className="flex gap-3"><Link to={`/movies/${hero.id}`} className="btn-primary"><Play size={16} />Book tickets</Link></div>
          </div>
        </section>
      )}

      {offers.length > 0 && (
        <section aria-label="Offers" className="flex gap-3 overflow-x-auto pb-1">
          {offers.map((o) => <div key={o.code} className="flex min-w-60 items-center gap-3 rounded-xl border border-edge bg-panel px-4 py-3"><Tag className="text-brand-soft" size={20} /><div><b className="tracking-widest">{o.code}</b><div className="text-xs text-slate-300">{o.description}</div></div></div>)}
        </section>
      )}

      <section className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <div role="tablist" className="flex rounded-xl border border-edge p-1">
            {[['now_showing', 'Now Showing'], ['coming_soon', 'Coming Soon']].map(([v, l]) => (
              <button key={v} role="tab" aria-selected={release === v} onClick={() => set('release', v)} className={`rounded-lg px-4 py-2 text-sm ${release === v ? 'bg-brand text-white' : 'text-slate-400'}`}>{l}</button>
            ))}
          </div>
          <select className="input !w-auto" aria-label="City" value={city} onChange={(e) => setCity(e.target.value)}>
            <option value="">All cities</option>{cities.map((c) => <option key={c}>{c}</option>)}
          </select>
          <select className="input !w-auto" aria-label="Language" value={language} onChange={(e) => set('language', e.target.value)}><option value="">Any language</option>{LANGS.map((l) => <option key={l}>{l}</option>)}</select>
          <select className="input !w-auto" aria-label="Genre" value={genre} onChange={(e) => set('genre', e.target.value)}><option value="">Any genre</option>{genres.map((g) => <option key={g}>{g}</option>)}</select>
          <select className="input !w-auto" aria-label="Sort" value={sort} onChange={(e) => set('sort', e.target.value)}>
            <option value="newest">Newest</option><option value="trending">Trending</option><option value="rating">Top rated</option><option value="title">A-Z</option>
          </select>
          <input className="input !w-48" placeholder="Search title…" aria-label="Search title" value={qInput} onChange={(e) => setQInput(e.target.value)} />
        </div>
        <ErrorBox>{error}</ErrorBox>
        {!data && !error ? <Spinner /> : data && data.items.length === 0 ? <Empty>No movies match these filters.</Empty> : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
            {data?.items.map((m) => <MovieCard key={m.id} movie={m} saved={saved.has(m.id)} onToggleWatch={toggleWatch} />)}
          </div>
        )}
        {pages > 1 && (
          <div className="flex items-center justify-center gap-3">
            <button className="btn-ghost" disabled={page <= 1} onClick={() => set('page', page - 1)}>Previous</button>
            <span className="text-sm text-slate-400">Page {page} of {pages}</span>
            <button className="btn-ghost" disabled={page >= pages} onClick={() => set('page', page + 1)}>Next</button>
          </div>
        )}
      </section>

      {top.length > 0 && !q && <Row title="Top rated" movies={top} />}
      {recent.length > 0 && !q && <Row title="Recently viewed" movies={recent} />}
    </div>
  )
}

function Row({ title, movies }) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-bold">{title}</h2>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">{movies.map((m) => <MovieCard key={m.id} movie={m} />)}</div>
    </section>
  )
}
