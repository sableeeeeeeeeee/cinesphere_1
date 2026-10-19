import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Copy, LayoutGrid, Plus, Trash2 } from 'lucide-react'
import api, { errInfo } from '../../services/api'
import { ErrorBox, Field, Modal, Spinner } from '../../components/ui'
import { useToast } from '../../context/ToastContext'

export default function Cinemas() {
  const toast = useToast()
  const [list, setList] = useState(null)
  const [cinemaForm, setCinemaForm] = useState(null)
  const [screenForm, setScreenForm] = useState(null)
  const [err, setErr] = useState('')
  const load = () => api.get('/admin/cinemas').then((r) => setList(r.data))
  useEffect(() => { load() }, [])
  const run = async (fn, msg) => { try { await fn(); toast(msg); setCinemaForm(null); setScreenForm(null); setErr(''); load() } catch (e) { const m = errInfo(e).message; setErr(m); toast(m, 'error') } }
  if (!list) return <Spinner />
  return (
    <div className="space-y-5">
      <div className="flex items-center"><h1 className="text-2xl font-bold">Cinemas &amp; screens</h1><button className="btn-primary ml-auto" onClick={() => setCinemaForm({ name: '', city: '', address: '', phone: '', amenities: '' })}><Plus size={16} />New cinema</button></div>
      {list.map((c) => (
        <section key={c.id} className="card space-y-3">
          <div className="flex flex-wrap items-center gap-2"><div><h2 className="font-bold">{c.name}</h2><p className="text-xs text-slate-400">{c.city} • {c.address} • {c.amenities.join(', ')}</p></div>
            <button className="btn-ghost ml-auto" onClick={() => setCinemaForm({ ...c, amenities: c.amenities.join(', '), id: c.id })}>Edit</button>
            <button className="btn-ghost" onClick={() => setScreenForm({ cinema_id: c.id, name: `Audi ${c.screens.length + 1}`, rows: 8, cols: 12, formats: '2D' })}><Plus size={14} />Screen</button></div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{c.screens.map((s) => (
            <div key={s.id} className="flex items-center gap-2 rounded-xl border border-edge p-3"><div className="min-w-0 flex-1"><b>{s.name}</b><div className="text-xs text-slate-400">{s.formats.join(', ')} • layout v{s.layout_version}</div></div>
              <Link to={`/admin/screens/${s.id}`} className="btn-primary !px-3 !py-1.5"><LayoutGrid size={14} />Layout</Link>
              <button className="btn-ghost !p-2" aria-label="Duplicate screen" onClick={() => run(() => api.post(`/admin/screens/${s.id}/duplicate`), 'Screen duplicated')}><Copy size={14} /></button>
              <button className="btn-danger !p-2" aria-label="Delete screen" onClick={() => window.confirm(`Delete ${s.name}? This cannot be undone.`) && run(() => api.delete(`/admin/screens/${s.id}`), 'Screen deleted')}><Trash2 size={14} /></button></div>))}
            {c.screens.length === 0 && <p className="text-sm text-slate-400">No screens yet.</p>}</div>
        </section>))}
      {cinemaForm && (
        <Modal title={cinemaForm.id ? 'Edit cinema' : 'New cinema'} onClose={() => setCinemaForm(null)}>
          <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); const body = { ...cinemaForm, amenities: cinemaForm.amenities.split(',').map((x) => x.trim()).filter(Boolean), phone: cinemaForm.phone || null }; run(() => cinemaForm.id ? api.patch(`/admin/cinemas/${cinemaForm.id}`, body) : api.post('/admin/cinemas', body), 'Cinema saved') }}>
            <ErrorBox>{err}</ErrorBox>
            {[['name', 'Name'], ['city', 'City'], ['address', 'Address'], ['phone', 'Phone'], ['amenities', 'Amenities (comma separated)']].map(([k, l]) => <Field key={k} label={l}><input className="input" required={k === 'name' || k === 'city'} value={cinemaForm[k] || ''} onChange={(e) => setCinemaForm({ ...cinemaForm, [k]: e.target.value })} /></Field>)}
            <button className="btn-primary w-full">Save</button></form></Modal>)}
      {screenForm && (
        <Modal title="New screen" onClose={() => setScreenForm(null)}>
          <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); run(() => api.post(`/admin/cinemas/${screenForm.cinema_id}/screens`, { name: screenForm.name, rows: +screenForm.rows, cols: +screenForm.cols, formats: screenForm.formats.split(',').map((x) => x.trim()).filter(Boolean) }), 'Screen created. Open its layout to customise seats.') }}>
            <ErrorBox>{err}</ErrorBox>
            <Field label="Screen name"><input className="input" required value={screenForm.name} onChange={(e) => setScreenForm({ ...screenForm, name: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-3"><Field label="Rows"><input className="input" type="number" min={1} max={40} value={screenForm.rows} onChange={(e) => setScreenForm({ ...screenForm, rows: e.target.value })} /></Field>
              <Field label="Columns"><input className="input" type="number" min={1} max={60} value={screenForm.cols} onChange={(e) => setScreenForm({ ...screenForm, cols: e.target.value })} /></Field></div>
            <Field label="Formats (comma separated)"><input className="input" value={screenForm.formats} onChange={(e) => setScreenForm({ ...screenForm, formats: e.target.value })} /></Field>
            <button className="btn-primary w-full">Create with starter grid</button></form></Modal>)}
    </div>
  )
}
