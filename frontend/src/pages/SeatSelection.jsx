import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Timer } from 'lucide-react'
import api, { errInfo } from '../services/api'
import SeatMap, { Legend } from '../components/SeatMap'
import { ErrorBox, Spinner } from '../components/ui'
import { useToast } from '../context/ToastContext'
import { getSessionId, mmss, useCountdown } from '../hooks/useSeatSession'
import { fmtDateTime, money } from '../utils/format'

export default function SeatSelection() {
  const { showId } = useParams()
  const nav = useNavigate()
  const toast = useToast()
  const session = getSessionId()
  const [map, setMap] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const goingToCheckout = useRef(false)

  const load = useCallback(() => api.get(`/shows/${showId}/seats`, { params: { session_id: session } })
    .then((r) => { setMap(r.data); setError('') }).catch((e) => setError(errInfo(e).message)), [showId, session])

  // Real-time-ish updates: poll every 3s and when the tab regains focus, so locks/bookings by others appear quickly.
  useEffect(() => {
    load()
    const t = setInterval(load, 3000)
    const onVis = () => document.visibilityState === 'visible' && load()
    document.addEventListener('visibilitychange', onVis)
    return () => { clearInterval(t); document.removeEventListener('visibilitychange', onVis) }
  }, [load])

  // Leaving the page without checking out releases the holds.
  useEffect(() => () => { if (!goingToCheckout.current) api.delete(`/shows/${showId}/locks`, { params: { session_id: session } }).catch(() => {}) }, [showId, session])

  const mine = map?.seats.filter((s) => s.status === 'mine') || []
  const left = useCountdown(map?.my_locks?.seconds_remaining, () => { toast('Your seat hold expired. Please choose your seats again.', 'error'); load() })

  const clickSeat = async (seat) => {
    if (busy) return
    setBusy(true)
    try {
      if (seat.status === 'mine') await api.delete(`/shows/${showId}/locks`, { params: { session_id: session, seat_ids: [seat.id] }, paramsSerializer: { indexes: null } })
      else await api.post(`/shows/${showId}/locks`, { seat_ids: [seat.id], session_id: session })
    } catch (e) {
      const info = errInfo(e)
      toast(info.status === 401 ? 'Please sign in to select seats' : info.message, 'error')
      if (info.status === 401) nav('/login', { state: { from: `/shows/${showId}/seats` } })
    } finally { await load(); setBusy(false) }
  }

  if (error && !map) return <ErrorBox>{error}</ErrorBox>
  if (!map) return <Spinner />
  const show = map.show
  const total = mine.reduce((a, s) => a + (s.price || 0), 0)
  const cats = [...new Set(map.seats.map((s) => s.category))]

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
      <section className="card space-y-6">
        <div><h1 className="text-2xl font-bold">{show.movie_title}</h1>
          <p className="text-sm text-slate-400">{show.cinema_name} • {show.screen_name} • {fmtDateTime(show.starts_at)} • {show.format}</p></div>
        <SeatMap seats={map.seats} rowLabels={map.row_labels} cols={map.cols} onSeat={clickSeat} />
        <Legend categories={cats} />
        <div className="flex flex-wrap justify-center gap-3 text-xs text-slate-400">
          {cats.map((c) => <span key={c} className="chip capitalize">{c}: {money(show.prices[c])}</span>)}
        </div>
      </section>

      <aside className="card h-fit space-y-4 lg:sticky lg:top-24">
        <h2 className="font-bold">Your selection</h2>
        {mine.length === 0 ? <p className="text-sm text-slate-400">Tap seats on the map to hold them for you.</p> : (
          <>
            <div className="flex items-center gap-2 rounded-xl bg-amber-500/10 px-3 py-2 text-amber-200" role="timer" aria-live="off">
              <Timer size={18} /><span>Seats held for</span><b className="ml-auto text-lg tabular-nums">{mmss(left)}</b>
            </div>
            <ul className="space-y-1 text-sm">{mine.map((s) => <li key={s.id} className="flex justify-between"><span>{s.row}{s.number} <span className="text-xs capitalize text-slate-400">{s.category}</span></span><span>{money(s.price)}</span></li>)}</ul>
            <div className="flex justify-between border-t border-edge pt-3 font-bold"><span>Tickets</span><span>{money(total)}</span></div>
            <p className="text-xs text-slate-500">Fees, tax, food and offers are added at checkout. Final price is always calculated by the server.</p>
            <button className="btn-primary w-full" onClick={() => { goingToCheckout.current = true; nav(`/checkout/${showId}`) }}>Continue to checkout</button>
          </>
        )}
      </aside>
    </div>
  )
}
