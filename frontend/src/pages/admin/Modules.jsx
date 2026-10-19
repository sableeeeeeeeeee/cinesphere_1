import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import api, { errInfo } from '../../services/api'
import { Empty, ErrorBox, Field, Modal, Spinner } from '../../components/ui'
import { useToast } from '../../context/ToastContext'
import { fmtDateTime, money } from '../../utils/format'

function useList(url, params) {
  const [data, setData] = useState(null)
  const load = () => api.get(url, { params }).then((r) => setData(r.data)).catch(() => setData([]))
  useEffect(() => { load() }, [url, JSON.stringify(params)]) // eslint-disable-line
  return [data, load]
}
function useAction(reload) {
  const toast = useToast()
  const [err, setErr] = useState('')
  const run = async (fn, msg) => { try { await fn(); msg && toast(msg); setErr(''); reload(); return true } catch (e) { const m = errInfo(e).message; setErr(m); toast(m, 'error'); return false } }
  return [run, err, setErr]
}
const Head = ({ title, children }) => <div className="mb-4 flex flex-wrap items-center gap-3"><h1 className="mr-auto text-2xl font-bold">{title}</h1>{children}</div>
const Table = ({ cols, children }) => <div className="card overflow-x-auto !p-0"><table className="w-full"><thead className="border-b border-edge"><tr>{cols.map((c) => <th key={c} className="th">{c}</th>)}</tr></thead><tbody className="divide-y divide-edge">{children}</tbody></table></div>
const utcFromLocal = (v) => new Date(v).toISOString()
const localFromUtc = (iso) => { const d = new Date(iso); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 16) }

// ------------------------------------------------------------------ movies
const blankMovie = { title: '', synopsis: '', poster_url: '', backdrop_url: '', trailer_url: '', director: '', cast: '', language: 'English', duration_min: 120, certificate: 'UA', release_date: '', status: 'published', genres: '' }
export function AdminMovies() {
  const [list, load] = useList('/admin/movies')
  const [run, err, setErr] = useAction(load)
  const [form, setForm] = useState(null)
  if (!list) return <Spinner />
  const save = async (e) => {
    e.preventDefault()
    const body = { ...form, cast: String(form.cast).split(',').map((x) => x.trim()).filter(Boolean), genres: String(form.genres).split(',').map((x) => x.trim()).filter(Boolean), release_date: form.release_date || null,
      poster_url: form.poster_url || null, backdrop_url: form.backdrop_url || null, trailer_url: form.trailer_url || null, duration_min: +form.duration_min }
    delete body.id; delete body.avg_rating; delete body.rating_count
    if (await run(() => form.id ? api.patch(`/admin/movies/${form.id}`, body) : api.post('/admin/movies', body), 'Movie saved')) setForm(null)
  }
  const f = (k) => ({ value: form?.[k] ?? '', onChange: (e) => setForm({ ...form, [k]: e.target.value }) })
  return (
    <div><Head title="Movies"><button className="btn-primary" onClick={() => { setErr(''); setForm(blankMovie) }}><Plus size={16} />Add movie</button></Head>
      <Table cols={['Title', 'Language', 'Genres', 'Status', 'Rating', '']}>{list.map((m) => (
        <tr key={m.id}><td className="td font-medium">{m.title}</td><td className="td">{m.language}</td><td className="td">{m.genres.join(', ')}</td>
          <td className="td"><span className="chip capitalize">{m.status}</span></td><td className="td">{m.rating_count ? `${m.avg_rating} (${m.rating_count})` : '–'}</td>
          <td className="td space-x-2 whitespace-nowrap"><button className="btn-ghost !py-1" onClick={() => { setErr(''); setForm({ ...m, cast: m.cast.join(', '), genres: m.genres.join(', '), release_date: m.release_date || '', poster_url: m.poster_url || '', backdrop_url: m.backdrop_url || '', trailer_url: m.trailer_url || '', director: m.director || '' }) }}>Edit</button>
            {m.status !== 'published' ? <button className="btn-ghost !py-1" onClick={() => run(() => api.patch(`/admin/movies/${m.id}`, { ...m, genres: m.genres, release_date: m.release_date, status: 'published' }), 'Published')}>Publish</button>
              : <button className="btn-ghost !py-1" onClick={() => run(() => api.patch(`/admin/movies/${m.id}`, { ...m, status: 'draft' }), 'Unpublished')}>Unpublish</button>}
            {m.status !== 'archived' && <button className="btn-danger !py-1" onClick={() => window.confirm(`Archive ${m.title}?`) && run(() => api.delete(`/admin/movies/${m.id}`), 'Archived')}>Archive</button>}</td></tr>))}</Table>
      {form && <Modal title={form.id ? 'Edit movie' : 'Add movie'} onClose={() => setForm(null)}>
        <form onSubmit={save} className="space-y-3"><ErrorBox>{err}</ErrorBox>
          <Field label="Title"><input className="input" required {...f('title')} /></Field>
          <Field label="Synopsis"><textarea className="input" rows={3} {...f('synopsis')} /></Field>
          <Field label="Poster URL"><input className="input" {...f('poster_url')} /></Field><Field label="Backdrop URL"><input className="input" {...f('backdrop_url')} /></Field>
          <Field label="Trailer embed URL (e.g. https://www.youtube.com/embed/ID)"><input className="input" {...f('trailer_url')} /></Field>
          <div className="grid grid-cols-2 gap-3"><Field label="Director"><input className="input" {...f('director')} /></Field><Field label="Language"><input className="input" {...f('language')} /></Field>
            <Field label="Runtime (min)"><input className="input" type="number" min={1} {...f('duration_min')} /></Field><Field label="Certificate"><input className="input" {...f('certificate')} /></Field>
            <Field label="Release date"><input className="input" type="date" {...f('release_date')} /></Field>
            <Field label="Status"><select className="input" {...f('status')}><option>published</option><option>draft</option><option>archived</option></select></Field></div>
          <Field label="Cast (comma separated)"><input className="input" {...f('cast')} /></Field><Field label="Genres (comma separated)"><input className="input" {...f('genres')} /></Field>
          <button className="btn-primary w-full">Save movie</button></form></Modal>}
    </div>
  )
}

// ------------------------------------------------------------------- shows
export function AdminShows() {
  const [list, load] = useList('/admin/shows')
  const [movies] = useList('/admin/movies')
  const [cinemas] = useList('/admin/cinemas')
  const [run, err, setErr] = useAction(load)
  const [form, setForm] = useState(null)
  const [viewing, setViewing] = useState(null)
  if (!list || !movies || !cinemas) return <Spinner />
  const screens = cinemas.flatMap((c) => c.screens.map((s) => ({ ...s, label: `${c.name} / ${s.name}` })))
  const open = async (screenId, base) => {
    const r = await api.get(`/admin/screens/${screenId}`)
    const cats = [...new Set(r.data.layout.cells.flat().filter(Boolean).map((c) => c.c))]
    const prices = Object.fromEntries(cats.map((c) => [c, base?.prices?.[c] != null ? base.prices[c] / 100 : 150]))
    setForm({ ...base, screen_id: screenId, prices })
  }
  const save = async (e) => {
    e.preventDefault()
    const body = { movie_id: +form.movie_id, screen_id: +form.screen_id, starts_at: utcFromLocal(form.starts_local), format: form.format, language: form.language,
      prices: Object.fromEntries(Object.entries(form.prices).map(([k, v]) => [k, Math.round(Number(v) * 100)])) }
    if (await run(() => form.id ? api.patch(`/admin/shows/${form.id}`, body) : api.post('/admin/shows', body), 'Show saved')) setForm(null)
  }
  return (
    <div><Head title="Showtimes"><button className="btn-primary" onClick={() => { setErr(''); setForm({ movie_id: movies[0]?.id, screen_id: '', starts_local: '', format: '2D', language: 'English', prices: {} }) }}><Plus size={16} />Add show</button></Head>
      <Table cols={['Movie', 'Cinema / screen', 'Starts', 'Format', 'Sold', 'Status', '']}>{list.map((s) => (
        <tr key={s.id}><td className="td font-medium">{s.movie_title}</td><td className="td">{s.cinema_name} / {s.screen_name}</td><td className="td">{fmtDateTime(s.starts_at)}</td><td className="td">{s.format}</td><td className="td">{s.tickets_sold}</td>
          <td className="td"><span className="chip capitalize">{s.status}</span></td>
          <td className="td space-x-2 whitespace-nowrap"><button className="btn-ghost !py-1" onClick={async () => setViewing({ show: s, rows: (await api.get(`/admin/shows/${s.id}/bookings`)).data })}>Bookings</button>
            {s.status === 'scheduled' && new Date(s.starts_at) > new Date() && <><button className="btn-ghost !py-1" onClick={() => { setErr(''); open(s.screen_id, { ...s, movie_id: s.movie_id, starts_local: localFromUtc(s.starts_at) }) }}>Edit</button>
              <button className="btn-danger !py-1" onClick={() => window.confirm('Cancel this show? All bookings are cancelled with a full refund.') && run(() => api.post(`/admin/shows/${s.id}/cancel`), 'Show cancelled')}>Cancel</button></>}</td></tr>))}</Table>
      {form && <Modal title={form.id ? 'Edit show' : 'Add show'} onClose={() => setForm(null)}>
        <form onSubmit={save} className="space-y-3"><ErrorBox>{err}</ErrorBox>
          <Field label="Movie"><select className="input" value={form.movie_id} onChange={(e) => setForm({ ...form, movie_id: e.target.value })}>{movies.filter((m) => m.status === 'published').map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}</select></Field>
          <Field label="Screen"><select className="input" required value={form.screen_id} onChange={(e) => e.target.value && open(e.target.value, { ...form })}><option value="">Select…</option>{screens.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}</select></Field>
          <Field label="Start (your local time)"><input className="input" type="datetime-local" required value={form.starts_local} onChange={(e) => setForm({ ...form, starts_local: e.target.value })} /></Field>
          <div className="grid grid-cols-2 gap-3"><Field label="Format"><input className="input" value={form.format} onChange={(e) => setForm({ ...form, format: e.target.value })} /></Field><Field label="Language"><input className="input" value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })} /></Field></div>
          {Object.keys(form.prices).length > 0 && <div><span className="label">Ticket price per seat category (₹)</span><div className="grid grid-cols-2 gap-3">{Object.entries(form.prices).map(([k, v]) => <label key={k} className="text-sm capitalize">{k}<input className="input" type="number" min={0} step="1" value={v} onChange={(e) => setForm({ ...form, prices: { ...form.prices, [k]: e.target.value } })} /></label>)}</div></div>}
          <button className="btn-primary w-full">Save show</button></form></Modal>}
      {viewing && <Modal title={`Bookings: ${viewing.show.movie_title}`} onClose={() => setViewing(null)}>{viewing.rows.length === 0 ? <p className="text-sm text-slate-400">No bookings yet.</p> : viewing.rows.map((b) => <div key={b.id} className="flex justify-between border-b border-edge py-2 text-sm"><span>{b.reference} • {b.seats.map((x) => x.label).join(', ')}</span><span className="capitalize">{b.status}</span></div>)}</Modal>}
    </div>
  )
}

// ---------------------------------------------------------------- bookings
export function AdminBookings() {
  const [q, setQ] = useState('')
  const [st, setSt] = useState('')
  const [list, load] = useList('/admin/bookings', { q: q || undefined, status: st || undefined })
  const [run] = useAction(load)
  return (
    <div><Head title="Bookings"><input className="input !w-64" placeholder="Reference, name or email" value={q} onChange={(e) => setQ(e.target.value)} />
      <select className="input !w-auto" value={st} onChange={(e) => setSt(e.target.value)}><option value="">All</option><option value="confirmed">Confirmed</option><option value="cancelled">Cancelled</option></select></Head>
      {!list ? <Spinner /> : list.length === 0 ? <Empty>No bookings found.</Empty> : <Table cols={['Reference', 'Customer', 'Movie', 'Seats', 'Total', 'Status', '']}>{list.map((b) => (
        <tr key={b.id}><td className="td font-mono">{b.reference}</td><td className="td">{b.customer}<div className="text-xs text-slate-500">{b.customer_email}</div></td><td className="td">{b.movie_title}<div className="text-xs text-slate-500">{fmtDateTime(b.starts_at)}</div></td>
          <td className="td">{b.seats.map((s) => s.label).join(', ')}</td><td className="td">{money(b.total)}</td><td className="td"><span className="chip capitalize">{b.status}</span>{b.checked_in_at && <span className="chip ml-1">used</span>}<div className="text-xs text-slate-500">{b.payment_status}</div></td>
          <td className="td">{b.status === 'confirmed' && new Date(b.starts_at) > new Date() && <button className="btn-danger !py-1" onClick={() => window.confirm('Cancel and fully refund this booking?') && run(() => api.post(`/admin/bookings/${b.id}/cancel`), 'Booking cancelled and refunded')}>Cancel</button>}</td></tr>))}</Table>}
    </div>
  )
}

// -------------------------------------------------------------------- food
const STATUSES = ['pending', 'confirmed', 'preparing', 'ready', 'delivered', 'cancelled']
export function AdminFood() {
  const [items, loadItems] = useList('/admin/food/items')
  const [orders, loadOrders] = useList('/admin/food/orders')
  const [run, err, setErr] = useAction(() => { loadItems(); loadOrders() })
  const [form, setForm] = useState(null)
  const canEdit = true
  if (!items || !orders) return <Spinner />
  const save = async (e) => {
    e.preventDefault()
    const body = { category: form.category, name: form.name, description: form.description || '', image_url: form.image_url || null, price: Math.round(Number(form.price) * 100), is_available: form.is_available, stock: form.stock === '' || form.stock == null ? null : +form.stock,
      sizes: String(form.sizes || '').split(',').map((x) => x.trim()).filter(Boolean).map((x) => { const [name, extra] = x.split(':'); return { name, extra: Math.round(Number(extra || 0) * 100) } }) }
    if (await run(() => form.id ? api.patch(`/admin/food/items/${form.id}`, body) : api.post('/admin/food/items', body), 'Item saved')) setForm(null)
  }
  return (
    <div className="space-y-8">
      <section><Head title="Food menu"><button className="btn-primary" onClick={() => { setErr(''); setForm({ category: 'Snacks', name: '', description: '', price: 100, is_available: true, stock: '', sizes: '' }) }}><Plus size={16} />Add item</button></Head>
        <Table cols={['Item', 'Category', 'Price', 'Stock', 'Available', '']}>{items.map((i) => (
          <tr key={i.id}><td className="td font-medium">{i.name}</td><td className="td">{i.category}</td><td className="td">{money(i.price)}</td><td className="td">{i.stock ?? '∞'}</td><td className="td">{i.is_available ? 'Yes' : 'No'}</td>
            <td className="td space-x-2"><button className="btn-ghost !py-1" onClick={() => { setErr(''); setForm({ ...i, price: i.price / 100, stock: i.stock ?? '', sizes: i.sizes.map((s) => `${s.name}:${s.extra / 100}`).join(', ') }) }}>Edit</button>
              <button className="btn-ghost !py-1" onClick={() => run(() => api.patch(`/admin/food/items/${i.id}`, { category: i.category, name: i.name, description: i.description, image_url: i.image_url, price: i.price, sizes: i.sizes, stock: i.stock, is_available: !i.is_available }), 'Updated')}>{i.is_available ? 'Deactivate' : 'Activate'}</button></td></tr>))}</Table></section>
      <section><Head title="Food orders" />{orders.length === 0 ? <Empty>No orders yet.</Empty> : <Table cols={['Order', 'Items', 'Type', 'Total', 'Status']}>{orders.map((o) => (
        <tr key={o.id}><td className="td font-mono">{o.order_number}</td><td className="td">{o.items.map((i) => `${i.quantity}× ${i.name}`).join(', ')}</td><td className="td">{o.fulfilment === 'seat_delivery' ? 'To seat' : 'Pickup'}</td><td className="td">{o.booking_id ? 'With booking' : money(o.total)}</td>
          <td className="td"><select className="input" value={o.status} onChange={(e) => run(() => api.patch(`/admin/food/orders/${o.id}`, { status: e.target.value }), 'Status updated')}>{STATUSES.map((s) => <option key={s}>{s}</option>)}</select></td></tr>))}</Table>}</section>
      {form && canEdit && <Modal title={form.id ? 'Edit item' : 'Add item'} onClose={() => setForm(null)}>
        <form onSubmit={save} className="space-y-3"><ErrorBox>{err}</ErrorBox>
          {[['category', 'Category'], ['name', 'Name'], ['description', 'Description'], ['image_url', 'Image URL']].map(([k, l]) => <Field key={k} label={l}><input className="input" required={k === 'name' || k === 'category'} value={form[k] || ''} onChange={(e) => setForm({ ...form, [k]: e.target.value })} /></Field>)}
          <div className="grid grid-cols-2 gap-3"><Field label="Price (₹)"><input className="input" type="number" min={0} step="0.5" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} /></Field>
            <Field label="Stock (blank = unlimited)"><input className="input" type="number" min={0} value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })} /></Field></div>
          <Field label="Sizes (Name:extra₹, e.g. Large:60)"><input className="input" value={form.sizes} onChange={(e) => setForm({ ...form, sizes: e.target.value })} /></Field>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.is_available} onChange={(e) => setForm({ ...form, is_available: e.target.checked })} />Available</label>
          <button className="btn-primary w-full">Save</button></form></Modal>}
    </div>
  )
}

// ----------------------------------------------------------------- reviews
export function AdminReviews() {
  const [list, load] = useList('/admin/reports')
  const [run] = useAction(load)
  if (!list) return <Spinner />
  return (
    <div><Head title="Reported reviews" />{list.length === 0 ? <Empty>No pending reports.</Empty> : list.map((r) => (
      <div key={r.id} className="card mb-3 space-y-2"><div className="text-sm"><b>{r.review.author}</b> • {r.review.rating}/5 stars</div><p className="text-slate-300">{r.review.text || <i>(no text)</i>}</p><p className="text-xs text-amber-300">Reported: {r.reason}</p>
        <div className="flex gap-2"><button className="btn-danger" onClick={() => run(() => api.post(`/admin/reports/${r.id}/remove`), 'Review removed')}>Remove review</button><button className="btn-ghost" onClick={() => run(() => api.post(`/admin/reports/${r.id}/dismiss`), 'Report dismissed')}>Dismiss</button></div></div>))}</div>
  )
}

// ------------------------------------------------------------------- users
export function AdminUsers() {
  const [q, setQ] = useState('')
  const [list, load] = useList('/admin/users', { q: q || undefined })
  const [run] = useAction(load)
  return (
    <div><Head title="Users"><input className="input !w-64" placeholder="Search name or email" value={q} onChange={(e) => setQ(e.target.value)} /></Head>
      {!list ? <Spinner /> : <Table cols={['Name', 'Email', 'Role', 'Status', '']}>{list.map((u) => (
        <tr key={u.id}><td className="td font-medium">{u.name}</td><td className="td">{u.email}</td>
          <td className="td"><select className="input !w-auto" value={u.role} onChange={(e) => run(() => api.patch(`/admin/users/${u.id}`, { role: e.target.value }), 'Role updated')}><option>customer</option><option>staff</option><option>admin</option></select></td>
          <td className="td">{u.is_active ? 'Active' : <span className="text-red-300">Suspended</span>}</td>
          <td className="td"><button className="btn-ghost !py-1" onClick={() => run(() => api.patch(`/admin/users/${u.id}`, { is_active: !u.is_active }), u.is_active ? 'Suspended' : 'Reactivated')}>{u.is_active ? 'Suspend' : 'Reactivate'}</button></td></tr>))}</Table>}</div>
  )
}

// ----------------------------------------------------------------- coupons
export function AdminCoupons() {
  const [list, load] = useList('/admin/coupons')
  const [run, err, setErr] = useAction(load)
  const [form, setForm] = useState(null)
  if (!list) return <Spinner />
  const save = async (e) => {
    e.preventDefault()
    const body = { code: form.code, kind: form.kind, value: form.kind === 'fixed' ? Math.round(form.value * 100) : +form.value, min_order: Math.round((form.min_order || 0) * 100), max_uses: form.max_uses ? +form.max_uses : null,
      max_discount: form.max_discount ? Math.round(form.max_discount * 100) : null, expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null, description: form.description }
    if (await run(() => api.post('/admin/coupons', body), 'Coupon created')) setForm(null)
  }
  return (
    <div><Head title="Coupons & offers"><button className="btn-primary" onClick={() => { setErr(''); setForm({ code: '', kind: 'percent', value: 10, min_order: 0, max_uses: '', max_discount: '', expires_at: '', description: '' }) }}><Plus size={16} />New coupon</button></Head>
      <Table cols={['Code', 'Discount', 'Min order', 'Used', 'Expires', 'Active']}>{list.map((c) => (
        <tr key={c.id}><td className="td font-mono font-bold">{c.code}<div className="text-xs font-normal text-slate-500">{c.description}</div></td><td className="td">{c.kind === 'percent' ? `${c.value}%` : money(c.value)}</td><td className="td">{money(c.min_order)}</td><td className="td">{c.used_count}{c.max_uses ? ` / ${c.max_uses}` : ''}</td><td className="td">{c.expires_at ? fmtDateTime(c.expires_at) : '–'}</td>
          <td className="td"><button className="btn-ghost !py-1" onClick={() => run(() => api.patch(`/admin/coupons/${c.id}/active`))}>{c.is_active ? 'On' : 'Off'}</button></td></tr>))}</Table>
      {form && <Modal title="New coupon" onClose={() => setForm(null)}><form onSubmit={save} className="space-y-3"><ErrorBox>{err}</ErrorBox>
        <Field label="Code"><input className="input" required minLength={3} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} /></Field>
        <div className="grid grid-cols-2 gap-3"><Field label="Type"><select className="input" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}><option value="percent">Percent</option><option value="fixed">Fixed (₹)</option></select></Field>
          <Field label={form.kind === 'percent' ? 'Percent' : 'Amount (₹)'}><input className="input" type="number" min={1} required value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} /></Field>
          <Field label="Min order (₹)"><input className="input" type="number" min={0} value={form.min_order} onChange={(e) => setForm({ ...form, min_order: e.target.value })} /></Field>
          <Field label="Max uses"><input className="input" type="number" min={1} value={form.max_uses} onChange={(e) => setForm({ ...form, max_uses: e.target.value })} /></Field>
          {form.kind === 'percent' && <Field label="Max discount (₹)"><input className="input" type="number" min={1} value={form.max_discount} onChange={(e) => setForm({ ...form, max_discount: e.target.value })} /></Field>}
          <Field label="Expires"><input className="input" type="datetime-local" value={form.expires_at} onChange={(e) => setForm({ ...form, expires_at: e.target.value })} /></Field></div>
        <Field label="Description"><input className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
        <button className="btn-primary w-full">Create</button></form></Modal>}</div>
  )
}

// ------------------------------------------------------------------- audit
export function AdminAudit() {
  const [list] = useList('/admin/audit-logs')
  if (!list) return <Spinner />
  return <div><Head title="Audit log" /><Table cols={['When', 'Actor', 'Action', 'Entity', 'Detail']}>{list.map((a) => <tr key={a.id}><td className="td whitespace-nowrap">{fmtDateTime(a.created_at)}</td><td className="td">#{a.actor_id}</td><td className="td font-mono text-xs">{a.action}</td><td className="td">{a.entity} {a.entity_id}</td><td className="td text-xs text-slate-400">{a.detail ? JSON.stringify(a.detail) : ''}</td></tr>)}</Table></div>
}

// ------------------------------------------------------- ticket validation
export function ValidateTicket() {
  const [ref, setRef] = useState('')
  const [res, setRes] = useState(null)
  const [err, setErr] = useState('')
  const check = async (e) => { e.preventDefault(); setErr(''); try { setRes((await api.post('/tickets/validate', { reference: ref })).data) } catch (x) { setErr(errInfo(x).message) } }
  return (
    <div className="mx-auto max-w-lg space-y-4"><h1 className="text-2xl font-bold">Validate ticket</h1>
      <form onSubmit={check} className="card space-y-3"><ErrorBox>{err}</ErrorBox><Field label="Booking reference (the QR code contains this text)"><input className="input text-lg tracking-widest" autoFocus required value={ref} onChange={(e) => setRef(e.target.value.toUpperCase())} /></Field>
        <button className="btn-primary w-full">Check &amp; admit</button><p className="text-xs text-slate-500">A valid ticket is marked as used immediately. Use a USB/phone QR scanner that types into this field, or enter the code by hand.</p></form>
      {res && <div className={`card border-2 ${res.valid ? 'border-emerald-600' : 'border-red-600'}`}><div className={`text-xl font-bold ${res.valid ? 'text-emerald-300' : 'text-red-300'}`}>{res.valid ? 'VALID: admit' : 'NOT VALID'}</div><p>{res.reason}</p>
        {res.movie_title && <p className="mt-2 text-sm text-slate-300">{res.movie_title} • {fmtDateTime(res.starts_at)} • Seats {res.seats?.join(', ')}</p>}</div>}
    </div>
  )
}
