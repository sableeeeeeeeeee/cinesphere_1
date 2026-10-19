import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Minus, Plus, Save } from 'lucide-react'
import api, { errInfo } from '../../services/api'
import { ErrorBox, Spinner } from '../../components/ui'
import { useToast } from '../../context/ToastContext'
import { CATEGORIES, CATEGORY_STYLES } from '../../utils/format'

const clone = (x) => JSON.parse(JSON.stringify(x))
const nextNumber = (row) => String(Math.max(0, ...row.filter(Boolean).map((c) => parseInt(c.n, 10) || 0)) + 1)

export default function ScreenEditor() {
  const { id } = useParams()
  const toast = useToast()
  const [screen, setScreen] = useState(null)
  const [layout, setLayout] = useState(null)
  const [sel, setSel] = useState(new Set()) // "r:c"
  const [errors, setErrors] = useState('')
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => { api.get(`/admin/screens/${id}`).then((r) => { setScreen(r.data); setLayout(r.data.layout) }).catch((e) => setErrors(errInfo(e).message)) }, [id])
  useEffect(() => { const h = (e) => dirty && (e.preventDefault(), (e.returnValue = '')); window.addEventListener('beforeunload', h); return () => window.removeEventListener('beforeunload', h) }, [dirty])

  const summary = useMemo(() => {
    const by = {}; let total = 0
    layout?.cells.forEach((row) => row.forEach((c) => { if (c) { total++; by[c.c] = (by[c.c] || 0) + 1 } }))
    return { total, by }
  }, [layout])
  if (!layout) return errors ? <ErrorBox>{errors}</ErrorBox> : <Spinner />

  const edit = (fn) => { const l = clone(layout); fn(l); setLayout(l); setDirty(true) }
  const each = (fn) => edit((l) => sel.forEach((k) => { const [r, c] = k.split(':').map(Number); fn(l, r, c) }))
  const toggle = (r, c) => setSel((s) => { const n = new Set(s); n.has(`${r}:${c}`) ? n.delete(`${r}:${c}`) : n.add(`${r}:${c}`); return n })
  const selectRow = (r) => setSel(new Set(Array.from({ length: layout.cols }, (_, c) => `${r}:${c}`)))
  const selectCol = (c) => setSel(new Set(layout.row_labels.map((_, r) => `${r}:${c}`)))
  const hasSeats = (cells) => cells.some((c) => c)

  const addRow = () => edit((l) => { const lab = nextLabel(l.row_labels); l.row_labels.push(lab); l.cells.push(Array.from({ length: l.cols }, (_, i) => ({ n: String(i + 1), c: 'standard', d: false }))) })
  const removeRow = () => {
    const r = layout.row_labels.length - 1
    if (r < 1) return
    if (hasSeats(layout.cells[r]) && !window.confirm(`Remove row ${layout.row_labels[r]} and its seats?`)) return
    edit((l) => { l.row_labels.pop(); l.cells.pop() }); setSel(new Set())
  }
  const addCol = () => edit((l) => { l.cols++; l.cells.forEach((row) => row.push({ n: nextNumber(row), c: 'standard', d: false })) })
  const removeCol = () => {
    if (layout.cols < 2) return
    if (layout.cells.some((row) => row[layout.cols - 1]) && !window.confirm('Remove the last column and its seats?')) return
    edit((l) => { l.cols--; l.cells.forEach((row) => row.pop()) }); setSel(new Set())
  }
  const renumber = () => edit((l) => l.cells.forEach((row) => { let n = 1; row.forEach((c) => { if (c && !/^[A-Za-z]/.test(c.n)) c.n = String(n++) }) }))

  const save = async () => {
    setSaving(true); setErrors('')
    try { const r = await api.put(`/admin/screens/${id}/layout`, layout); setScreen(r.data); setLayout(r.data.layout); setDirty(false); toast('Layout saved') }
    catch (e) { setErrors(errInfo(e).message) } finally { setSaving(false) }
  }
  const one = sel.size === 1 ? [...sel][0].split(':').map(Number) : null
  const oneCell = one && layout.cells[one[0]][one[1]]

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <div><h1 className="text-2xl font-bold">Layout editor: {screen.name}</h1><p className="text-sm text-slate-400">Click seats to select them, then apply an action. Click a row letter or column number to select the whole line.</p></div>
        <button className="btn-primary ml-auto" onClick={save} disabled={saving}><Save size={16} />{saving ? 'Saving…' : dirty ? 'Save layout *' : 'Save layout'}</button>
      </div>
      <ErrorBox>{errors}</ErrorBox>

      <div className="card flex flex-wrap items-center gap-2 text-sm">
        <b className="mr-2">Grid</b>
        <button className="btn-ghost !px-2" onClick={removeRow} aria-label="Remove last row"><Minus size={14} /></button><span>{layout.row_labels.length} rows</span><button className="btn-ghost !px-2" onClick={addRow} aria-label="Add row"><Plus size={14} /></button>
        <span className="mx-2 text-slate-600">|</span>
        <button className="btn-ghost !px-2" onClick={removeCol} aria-label="Remove last column"><Minus size={14} /></button><span>{layout.cols} columns</span><button className="btn-ghost !px-2" onClick={addCol} aria-label="Add column"><Plus size={14} /></button>
        <button className="btn-ghost ml-auto" onClick={renumber}>Auto-number rows</button>
      </div>

      <div className="card flex flex-wrap items-center gap-2 text-sm">
        <b className="mr-2">{sel.size} selected</b>
        <button className="btn-ghost" onClick={() => setSel(new Set(layout.cells.flatMap((row, r) => row.map((_, c) => `${r}:${c}`))))}>Select all</button>
        <button className="btn-ghost" onClick={() => setSel(new Set())}>Clear</button>
        <span className="mx-1 text-slate-600">|</span>
        {CATEGORIES.map((c) => <button key={c} disabled={!sel.size} className={`rounded-lg px-2.5 py-1.5 text-xs capitalize disabled:opacity-40 ${CATEGORY_STYLES[c]}`} onClick={() => each((l, r, col) => { const cell = l.cells[r][col]; l.cells[r][col] = cell ? { ...cell, c } : { n: nextNumber(l.cells[r]), c, d: false } })}>{c}</button>)}
        <span className="mx-1 text-slate-600">|</span>
        <button className="btn-ghost" disabled={!sel.size} onClick={() => each((l, r, c) => { l.cells[r][c] = null })}>Make empty / aisle</button>
        <button className="btn-ghost" disabled={!sel.size} onClick={() => each((l, r, c) => { const x = l.cells[r][c]; if (x) x.d = !x.d })}>Toggle disabled</button>
        {oneCell && <label className="ml-2 flex items-center gap-2 text-xs">Seat number <input className="input !w-20 !py-1" value={oneCell.n} maxLength={6} onChange={(e) => edit((l) => { l.cells[one[0]][one[1]].n = e.target.value })} /></label>}
      </div>

      <div className="card overflow-x-auto">
        <div className="mx-auto mb-1 h-2 w-3/4 rounded-full bg-gradient-to-r from-transparent via-brand-soft to-transparent" />
        <p className="mb-4 text-center text-[11px] uppercase tracking-[0.4em] text-slate-500">Screen</p>
        <div className="mx-auto w-max space-y-1.5">
          <div className="flex items-center gap-1.5"><span className="w-14" />{Array.from({ length: layout.cols }, (_, c) => <button key={c} className="w-9 text-center text-[10px] text-slate-500 hover:text-white" onClick={() => selectCol(c)} aria-label={`Select column ${c + 1}`}>{c + 1}</button>)}</div>
          {layout.row_labels.map((label, r) => (
            <div key={r} className="flex items-center gap-1.5">
              <input aria-label={`Row ${r + 1} label`} className="input !w-14 !px-1 !py-1 text-center text-xs" value={label} maxLength={4} onChange={(e) => edit((l) => { l.row_labels[r] = e.target.value.toUpperCase() })} onDoubleClick={() => selectRow(r)} title="Edit row label. Double-click to select the row" />
              {layout.cells[r].map((cell, c) => {
                const on = sel.has(`${r}:${c}`)
                return (
                  <button key={c} onClick={() => toggle(r, c)} aria-pressed={on} aria-label={cell ? `${label}${cell.n} ${cell.c}${cell.d ? ' disabled' : ''}` : `${label} empty space ${c + 1}`}
                    className={`seat ${cell ? `${CATEGORY_STYLES[cell.c]} ${cell.d ? 'opacity-40 line-through' : ''}` : 'border border-dashed border-slate-700 text-slate-700'} ${on ? 'ring-2 ring-white' : ''}`}>
                    {cell ? cell.n : '·'}
                  </button>)
              })}
            </div>))}
        </div>
        <div className="mt-4 flex flex-wrap justify-center gap-2 text-xs">{CATEGORIES.map((c) => <span key={c} className={`rounded px-2 py-0.5 capitalize ${CATEGORY_STYLES[c]}`}>{c}</span>)}<span className="chip">· empty / aisle</span><span className="chip line-through">disabled</span></div>
      </div>

      <div className="card text-sm"><b>Preview:</b> {summary.total} seats ({layout.row_labels.length} × {layout.cols} grid = {layout.row_labels.length * layout.cols} positions).
        <span className="ml-2 text-slate-300">{Object.entries(summary.by).map(([k, v]) => `${k}: ${v}`).join(' • ')}</span>
        <p className="mt-1 text-xs text-slate-500">Seats that have active bookings or holds cannot be removed, re-categorised or disabled. The server will refuse the save and tell you which seats.</p></div>
    </div>
  )
}

function nextLabel(labels) {
  const last = labels[labels.length - 1] || '@'
  if (/^[A-Y]$/.test(last)) return String.fromCharCode(last.charCodeAt(0) + 1)
  return last.length === 1 ? 'AA' : last.slice(0, -1) + String.fromCharCode(last.charCodeAt(last.length - 1) + 1)
}
