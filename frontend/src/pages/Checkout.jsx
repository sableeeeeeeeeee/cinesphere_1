import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Timer, TicketPercent } from 'lucide-react'
import api, { errInfo } from '../services/api'
import FoodPicker from '../components/FoodPicker'
import { ErrorBox, Spinner } from '../components/ui'
import { useToast } from '../context/ToastContext'
import { getSessionId, mmss, useCountdown } from '../hooks/useSeatSession'
import { fmtDateTime, money, uid } from '../utils/format'

export default function Checkout() {
  const { showId } = useParams()
  const nav = useNavigate()
  const toast = useToast()
  const session = getSessionId()
  const [map, setMap] = useState(null)
  const [cart, setCart] = useState([])
  const [coupon, setCoupon] = useState('')
  const [applied, setApplied] = useState('')
  const [couponErr, setCouponErr] = useState('')
  const [fulfilment, setFulfilment] = useState('pickup')
  const [quote, setQuote] = useState(null)
  const [err, setErr] = useState('')
  const [paying, setPaying] = useState(false)
  const [simFail, setSimFail] = useState(false)
  const idem = useRef(uid()) // reused on retry so a double-click can never create two bookings

  const loadMap = () => api.get(`/shows/${showId}/seats`, { params: { session_id: session } }).then((r) => {
    setMap(r.data)
    if (!r.data.my_locks?.seat_ids.length) { toast('Your seat hold has expired. Please pick seats again.', 'error'); nav(`/shows/${showId}/seats`, { replace: true }) }
  })
  useEffect(() => { loadMap().catch((e) => setErr(errInfo(e).message)) }, []) // eslint-disable-line

  const seatIds = map?.my_locks?.seat_ids || []
  const left = useCountdown(map?.my_locks?.seconds_remaining, () => { toast('Your seat hold expired.', 'error'); nav(`/shows/${showId}/seats`, { replace: true }) })

  // Every change asks the SERVER for the price. The client never computes the total.
  useEffect(() => {
    if (!seatIds.length) return
    api.post(`/shows/${showId}/quote`, { seat_ids: seatIds, food: cart, coupon_code: applied || null })
      .then((r) => { setQuote(r.data); setCouponErr('') })
      .catch((e) => { const i = errInfo(e); if (applied && i.code?.startsWith('coupon')) { setCouponErr(i.message); setApplied('') } else setErr(i.message) })
  }, [seatIds.join(','), JSON.stringify(cart), applied]) // eslint-disable-line

  const pay = async () => {
    setPaying(true); setErr('')
    try {
      const { data } = await api.post('/bookings/checkout', { show_id: Number(showId), session_id: session, seat_ids: seatIds, idempotency_key: idem.current, food: cart, coupon_code: applied || null, fulfilment, simulate_failure: simFail })
      toast(`Booking confirmed: ${data.reference}`); nav(`/bookings/${data.id}`, { replace: true })
    } catch (e) {
      const i = errInfo(e); setErr(i.message)
      if (['lock_expired', 'lock_not_owned', 'seat_already_booked'].includes(i.code)) setTimeout(() => nav(`/shows/${showId}/seats`), 2500)
    } finally { setPaying(false) }
  }

  if (!map) return err ? <ErrorBox>{err}</ErrorBox> : <Spinner />
  const show = map.show
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
      <div className="space-y-6">
        <section className="card"><h1 className="text-2xl font-bold">{show.movie_title}</h1>
          <p className="text-sm text-slate-400">{show.cinema_name} • {show.screen_name} • {fmtDateTime(show.starts_at)}</p></section>
        <section className="card space-y-4"><h2 className="font-bold">Add food &amp; drinks <span className="text-sm font-normal text-slate-400">(optional)</span></h2>
          <FoodPicker cart={cart} setCart={setCart} />
          {cart.length > 0 && <div className="flex gap-4 text-sm"><label className="flex items-center gap-2"><input type="radio" checked={fulfilment === 'pickup'} onChange={() => setFulfilment('pickup')} />Collect at counter</label>
            <label className="flex items-center gap-2"><input type="radio" checked={fulfilment === 'seat_delivery'} onChange={() => setFulfilment('seat_delivery')} />Deliver to my seat</label></div>}
        </section>
      </div>

      <aside className="card h-fit space-y-4 lg:sticky lg:top-24">
        <div className="flex items-center gap-2 rounded-xl bg-amber-500/10 px-3 py-2 text-amber-200" role="timer"><Timer size={18} />Seats held for<b className="ml-auto tabular-nums">{mmss(left)}</b></div>
        <h2 className="font-bold">Order summary</h2>
        {!quote ? <Spinner label="Calculating…" /> : (
          <div className="space-y-2 text-sm">
            {quote.seats.map((s) => <Row key={s.seat_id} l={`Seat ${s.label} (${s.category})`} r={money(s.price)} />)}
            {quote.food.map((f) => <Row key={f.item_id + (f.size || '')} l={`${f.quantity}× ${f.name}${f.size ? ` (${f.size})` : ''}`} r={money(f.unit_price * f.quantity)} />)}
            {quote.discount > 0 && <Row l={`Discount (${quote.coupon_code})`} r={`−${money(quote.discount)}`} cls="text-emerald-300" />}
            <Row l="Convenience fee" r={money(quote.fee)} cls="text-slate-400" /><Row l="Taxes" r={money(quote.tax)} cls="text-slate-400" />
            <div className="flex justify-between border-t border-edge pt-3 text-lg font-bold"><span>Total</span><span>{money(quote.total)}</span></div>
          </div>)}
        <div className="flex gap-2"><input className="input" placeholder="Coupon code" aria-label="Coupon code" value={coupon} onChange={(e) => setCoupon(e.target.value.toUpperCase())} />
          <button className="btn-ghost" onClick={() => { setApplied(coupon); setCouponErr('') }}><TicketPercent size={16} />Apply</button></div>
        {couponErr && <p className="text-xs text-red-300">{couponErr}</p>}
        <ErrorBox>{err}</ErrorBox>
        <div className="rounded-xl border border-amber-700/50 bg-amber-950/30 p-3 text-xs text-amber-200">
          <b>Development payment simulator.</b> No real money is charged and no card details are collected.
          <label className="mt-2 flex items-center gap-2"><input type="checkbox" checked={simFail} onChange={(e) => setSimFail(e.target.checked)} />Simulate a payment failure</label>
        </div>
        <button className="btn-primary w-full" disabled={paying || !quote} onClick={pay}>{paying ? 'Processing…' : `Pay ${quote ? money(quote.total) : ''}`}</button>
      </aside>
    </div>
  )
}
const Row = ({ l, r, cls = '' }) => <div className={`flex justify-between gap-3 ${cls}`}><span>{l}</span><span className="shrink-0">{r}</span></div>
