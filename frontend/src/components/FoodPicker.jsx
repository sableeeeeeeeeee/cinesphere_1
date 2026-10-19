import { useEffect, useState } from 'react'
import { Minus, Plus } from 'lucide-react'
import api from '../services/api'
import { money } from '../utils/format'
import { Spinner } from './ui'

/** cart: [{item_id, size, quantity}] */
export default function FoodPicker({ cart, setCart }) {
  const [menu, setMenu] = useState(null)
  const [sizes, setSizes] = useState({})
  useEffect(() => { api.get('/food/items').then((r) => setMenu(r.data)) }, [])
  const qty = (id, size) => cart.find((c) => c.item_id === id && (c.size || null) === (size || null))?.quantity || 0
  const change = (id, size, d) => setCart((c) => {
    const i = c.findIndex((x) => x.item_id === id && (x.size || null) === (size || null))
    if (i === -1) return d > 0 ? [...c, { item_id: id, size: size || null, quantity: 1 }] : c
    const q = c[i].quantity + d
    return q <= 0 ? c.filter((_, k) => k !== i) : c.map((x, k) => (k === i ? { ...x, quantity: Math.min(q, 20) } : x))
  })
  if (!menu) return <Spinner />
  return (
    <div className="space-y-5">
      {menu.filter((c) => c.items.length).map((cat) => (
        <div key={cat.id}><h4 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">{cat.name}</h4>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {cat.items.map((it) => {
              const size = sizes[it.id] ?? it.sizes[0]?.name ?? null
              const extra = it.sizes.find((s) => s.name === size)?.extra || 0
              const q = qty(it.id, size)
              return (
                <div key={it.id} className={`overflow-hidden rounded-xl border border-edge bg-ink ${it.is_available ? '' : 'opacity-50'}`}>
                  <div className="aspect-[4/3] overflow-hidden bg-edge">
                    {it.image_url && <img src={it.image_url} alt={it.name} loading="lazy" className="h-full w-full object-cover transition duration-500 hover:scale-105" />}
                  </div>
                  <div className="space-y-2 p-3">
                    <div><div className="font-semibold">{it.name}</div><div className="line-clamp-2 text-xs text-slate-400">{it.description}</div></div>
                    {it.sizes.length > 0 && <select aria-label={`${it.name} size`} className="input" value={size} onChange={(e) => setSizes({ ...sizes, [it.id]: e.target.value })}>{it.sizes.map((s) => <option key={s.name}>{s.name}</option>)}</select>}
                    <div className="flex items-center justify-between">
                      <span className="font-semibold">{money(it.price + extra)}</span>
                      {!it.is_available ? <span className="text-xs text-red-300">Unavailable</span> : q === 0 ? <button className="btn-primary !px-4 !py-1.5" onClick={() => change(it.id, size, 1)}>Add</button> : (
                        <span className="flex items-center gap-2"><button aria-label="Decrease" className="btn-ghost !p-1.5" onClick={() => change(it.id, size, -1)}><Minus size={14} /></button><b className="w-5 text-center">{q}</b><button aria-label="Increase" className="btn-ghost !p-1.5" onClick={() => change(it.id, size, 1)}><Plus size={14} /></button></span>)}
                    </div>
                  </div>
                </div>)
            })}
          </div></div>))}
    </div>
  )
}
