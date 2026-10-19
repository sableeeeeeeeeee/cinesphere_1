import { Loader2, Star } from 'lucide-react'

export const Spinner = ({ label = 'Loading…' }) => (
  <div className="flex items-center justify-center gap-2 py-16 text-slate-400" role="status"><Loader2 className="animate-spin" size={20} />{label}</div>
)
export const Empty = ({ children }) => <div className="rounded-xl border border-dashed border-edge py-12 text-center text-slate-400">{children}</div>
export const ErrorBox = ({ children }) => children ? <div className="whitespace-pre-line rounded-xl border border-red-800 bg-red-950/50 px-4 py-3 text-sm text-red-200" role="alert">{children}</div> : null
export const Field = ({ label, children }) => <label className="block"><span className="label">{label}</span>{children}</label>
export const Stars = ({ value, size = 15 }) => (
  <span className="inline-flex items-center gap-0.5 align-middle text-amber-400" role="img" aria-label={`${value} out of 5`}>
    {[1, 2, 3, 4, 5].map((n) => <Star key={n} size={size} fill={n <= Math.round(value) ? 'currentColor' : 'none'} className={n <= Math.round(value) ? '' : 'text-slate-600'} />)}
  </span>
)
export function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal="true" aria-label={title} onClick={onClose}>
      <div className="card max-h-[90vh] w-full max-w-md overflow-auto" onClick={(e) => e.stopPropagation()}>
        <h3 className="mb-3 text-lg font-bold">{title}</h3>{children}
      </div>
    </div>
  )
}
