import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import FoodPicker from '../components/FoodPicker'
import api, { errInfo } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { money } from '../utils/format'

export default function Food() {
  const { user } = useAuth()
  const nav = useNavigate()
  const toast = useToast()
  const [cart, setCart] = useState([])
  const [fulfilment, setFulfilment] = useState('pickup')
  const [busy, setBusy] = useState(false)
  const order = async () => {
    if (!user) return nav('/login', { state: { from: '/food' } })
    setBusy(true)
    try { const r = await api.post('/food/orders', { items: cart, fulfilment }); toast(`Order ${r.data.order_number} placed: ${money(r.data.total)}`); setCart([]) }
    catch (e) { toast(errInfo(e).message, 'error') } finally { setBusy(false) }
  }
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
      <section className="card space-y-4"><h1 className="text-2xl font-bold">Food &amp; beverages</h1><FoodPicker cart={cart} setCart={setCart} /></section>
      <aside className="card h-fit space-y-3">
        <h2 className="font-bold">Your cart</h2>
        <p className="text-sm text-slate-400">{cart.length ? `${cart.reduce((a, c) => a + c.quantity, 0)} item(s). Taxes and the final total are calculated by the server when you order.` : 'Add items from the menu.'}</p>
        <label className="flex items-center gap-2 text-sm"><input type="radio" checked={fulfilment === 'pickup'} onChange={() => setFulfilment('pickup')} />Collect at counter</label>
        <label className="flex items-center gap-2 text-sm"><input type="radio" checked={fulfilment === 'seat_delivery'} onChange={() => setFulfilment('seat_delivery')} />Deliver to seat</label>
        <button className="btn-primary w-full" disabled={!cart.length || busy} onClick={order}>Place order</button>
        <p className="text-xs text-slate-500">Booking tickets? Add food during checkout instead.</p>
      </aside>
    </div>
  )
}
