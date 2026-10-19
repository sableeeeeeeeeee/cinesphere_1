import { CATEGORY_STYLES } from '../utils/format'

const STATE = {
  available: '',
  selected: '!bg-brand !text-white ring-2 ring-white',
  locked: '!bg-amber-500/30 !text-amber-200 cursor-not-allowed',
  booked: '!bg-slate-800 !text-slate-600 cursor-not-allowed line-through',
  disabled: '!bg-transparent border border-dashed border-slate-700 !text-slate-700 cursor-not-allowed',
}

export function Legend({ categories = [] }) {
  const Item = ({ cls, children }) => <span className="flex items-center gap-2"><span className={`seat !h-5 !w-5 ${cls}`} />{children}</span>
  return (
    <div className="flex flex-wrap justify-center gap-x-5 gap-y-2 text-xs text-slate-400" aria-label="Seat legend">
      <Item cls="bg-slate-600">Available</Item><Item cls={STATE.selected}>Selected</Item><Item cls={STATE.locked}>Held by someone</Item>
      <Item cls={STATE.booked}>Booked</Item><Item cls={STATE.disabled}>Unavailable</Item>
      {categories.map((c) => <Item key={c} cls={CATEGORY_STYLES[c]}>{c}</Item>)}
    </div>
  )
}

/** Renders the saved layout: seats are placed by their stored grid position, so aisles/gaps appear automatically. */
export default function SeatMap({ seats, rowLabels, cols, onSeat }) {
  const byPos = new Map(seats.map((s) => [`${s.grid_row}:${s.grid_col}`, s]))
  return (
    <div className="overflow-x-auto pb-2">
      <div className="mx-auto w-max min-w-full px-2">
        <div className="mx-auto mb-1 h-2 w-3/4 rounded-full bg-gradient-to-r from-transparent via-brand-soft to-transparent shadow-[0_8px_30px_rgba(251,113,133,0.5)]" />
        <p className="mb-5 text-center text-[11px] uppercase tracking-[0.4em] text-slate-500">Screen this way</p>
        <div role="grid" aria-label="Seat map" className="space-y-1.5">
          {rowLabels.map((label, r) => (
            <div key={label} role="row" className="flex items-center justify-center gap-1.5">
              <span className="w-6 text-center text-xs text-slate-500" aria-hidden>{label}</span>
              {Array.from({ length: cols }, (_, c) => {
                const s = byPos.get(`${r}:${c}`)
                if (!s) return <span key={c} className="seat" aria-hidden />
                const st = s.status === 'mine' ? 'selected' : s.status
                const usable = st === 'available' || st === 'selected'
                return (
                  <button key={c} role="gridcell" disabled={!usable} onClick={() => onSeat(s)}
                    aria-label={`Seat ${s.row}${s.number}, ${s.category}, ${s.price != null ? '₹' + s.price / 100 : 'no price'}, ${st}`} aria-pressed={st === 'selected'}
                    title={`${s.row}${s.number} • ${s.category}`}
                    className={`seat ${CATEGORY_STYLES[s.category]} ${STATE[st]} ${usable ? 'hover:scale-110' : ''}`}>
                    {s.number}
                  </button>
                )
              })}
              <span className="w-6 text-center text-xs text-slate-500" aria-hidden>{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
