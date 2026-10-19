import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import { Printer } from 'lucide-react'
import api, { errInfo } from '../services/api'
import { Empty, ErrorBox, Spinner } from '../components/ui'
import { useToast } from '../context/ToastContext'
import { fmtDateTime, money } from '../utils/format'

export function MyBookings() {
  const [data, setData] = useState(null)
  const [tab, setTab] = useState('upcoming')
  const [orders, setOrders] = useState([])
  useEffect(() => { api.get('/bookings/my').then((r) => setData(r.data)); api.get('/food/orders/my').then((r) => setOrders(r.data)) }, [])
  if (!data) return <Spinner />
  const list = tab === 'food' ? [] : data[tab]
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">My bookings</h1>
      <div className="flex gap-2">{[['upcoming', 'Upcoming'], ['past', 'Past'], ['cancelled', 'Cancelled'], ['food', 'Food orders']].map(([k, l]) => (
        <button key={k} onClick={() => setTab(k)} className={`chip ${tab === k ? 'border-brand text-white' : ''}`}>{l}{k !== 'food' && ` (${data[k].length})`}</button>))}</div>
      {tab === 'food' ? (orders.length === 0 ? <Empty>No food orders yet.</Empty> : orders.map((o) => (
        <div key={o.id} className="card flex flex-wrap justify-between gap-2"><div><b>{o.order_number}</b><div className="text-sm text-slate-400">{o.items.map((i) => `${i.quantity}× ${i.name}`).join(', ')}</div></div>
          <div className="text-right"><span className="chip capitalize">{o.status}</span><div className="mt-1 text-sm">{o.booking_id ? 'With booking' : money(o.total)}</div></div></div>)))
        : list.length === 0 ? <Empty>Nothing here yet. <Link className="text-brand-soft" to="/">Find a movie</Link></Empty> : (
          <div className="grid gap-4 md:grid-cols-2">{list.map((b) => (
            <Link key={b.id} to={`/bookings/${b.id}`} className="card flex gap-4 transition hover:border-brand-soft">
              {b.poster_url && <img src={b.poster_url} alt="" className="h-28 w-20 rounded-lg object-cover" />}
              <div className="space-y-1"><h3 className="font-semibold">{b.movie_title}</h3><p className="text-xs text-slate-400">{b.cinema_name} • {b.screen_name}</p>
                <p className="text-sm">{fmtDateTime(b.starts_at)}</p><p className="text-sm text-slate-300">Seats: {b.seats.map((s) => s.label).join(', ')}</p>
                <p className="text-xs text-slate-500">Ref {b.reference} • {money(b.total)}</p></div></Link>))}</div>)}
    </div>
  )
}

export function Ticket() {
  const { id } = useParams()
  const toast = useToast()
  const [b, setB] = useState(null)
  const [policy, setPolicy] = useState(null)
  const [err, setErr] = useState('')
  const load = () => api.get(`/bookings/${id}`).then((r) => setB(r.data)).catch((e) => setErr(errInfo(e).message))
  useEffect(() => { load(); api.get('/cancellation-policy').then((r) => setPolicy(r.data)) }, [id]) // eslint-disable-line
  if (err) return <ErrorBox>{err}</ErrorBox>
  if (!b) return <Spinner />
  const upcoming = b.status === 'confirmed' && new Date(b.starts_at) > new Date() && !b.checked_in_at
  const cancel = async () => {
    if (!window.confirm('Cancel this booking? Refund depends on how close the show is.')) return
    try { const r = await api.post(`/bookings/${id}/cancel`); toast(`Cancelled. Refund: ${money(r.data.refund_amount)}`); load() } catch (e) { toast(errInfo(e).message, 'error') }
  }
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className={`card space-y-5 ${b.status === 'cancelled' ? 'opacity-70' : ''}`}>
        <div className="flex items-start justify-between gap-4">
          <div><span className={`chip ${b.status === 'confirmed' ? 'border-emerald-600 text-emerald-300' : 'border-red-600 text-red-300'}`}>{b.checked_in_at ? 'Used' : b.status}</span>
            <h1 className="mt-2 text-2xl font-bold">{b.movie_title}</h1><p className="text-sm text-slate-400">{b.cinema_name} • {b.screen_name}</p><p className="mt-1">{fmtDateTime(b.starts_at)}</p></div>
          <div className="rounded-xl bg-white p-2"><QRCodeSVG value={b.reference} size={110} /></div>
        </div>
        <div className="grid grid-cols-2 gap-4 border-y border-dashed border-edge py-4 text-sm">
          <div><div className="label">Booking reference</div><b className="text-lg tracking-widest">{b.reference}</b></div>
          <div><div className="label">Seats</div><b>{b.seats.map((s) => s.label).join(', ')}</b></div>
        </div>
        <div className="space-y-1 text-sm">
          <R l="Tickets" r={money(b.tickets_total)} />{b.food_total > 0 && <R l="Food" r={money(b.food_total)} />}{b.discount > 0 && <R l={`Discount (${b.coupon_code})`} r={`−${money(b.discount)}`} />}
          <R l="Fees" r={money(b.fee)} /><R l="Taxes" r={money(b.tax)} /><div className="flex justify-between border-t border-edge pt-2 font-bold"><span>Total paid</span><span>{money(b.total)}</span></div>
          {b.status === 'cancelled' && <R l="Refunded" r={money(b.refund_amount)} />}
        </div>
        {b.food_orders?.map((o) => <div key={o.id} className="rounded-xl bg-ink p-3 text-sm"><b>Food order {o.order_number}</b> <span className="chip ml-2 capitalize">{o.status}</span><div className="text-slate-400">{o.items.map((i) => `${i.quantity}× ${i.name}${i.size ? ` (${i.size})` : ''}`).join(', ')} • {o.fulfilment === 'seat_delivery' ? 'Delivered to seat' : 'Collect at counter'}</div></div>)}
      </div>
      <div className="flex flex-wrap gap-3 print:hidden">
        <button className="btn-ghost" onClick={() => window.print()}><Printer size={16} />Print / save as PDF</button>
        {upcoming && <button className="btn-danger" onClick={cancel}>Cancel booking</button>}
      </div>
      {upcoming && policy && <p className="text-xs text-slate-500 print:hidden">Refund policy: {policy.tiers.map((t) => `${t.percent}% if cancelled ${t.hours}h or more before the show`).join('; ')}; otherwise none. The convenience fee is non-refundable.</p>}
    </div>
  )
}
const R = ({ l, r }) => <div className="flex justify-between"><span className="text-slate-400">{l}</span><span>{r}</span></div>
