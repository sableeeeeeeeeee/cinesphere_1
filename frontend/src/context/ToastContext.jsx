import { createContext, useCallback, useContext, useState } from 'react'
import { CheckCircle2, XCircle } from 'lucide-react'

const Ctx = createContext(null)
export const useToast = () => useContext(Ctx)

export function ToastProvider({ children }) {
  const [items, setItems] = useState([])
  const push = useCallback((message, type = 'success') => {
    const id = Math.random()
    setItems((x) => [...x, { id, message, type }])
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 4500)
  }, [])
  return (
    <Ctx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex max-w-sm flex-col gap-2" role="status" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={`flex items-start gap-2 rounded-xl border px-4 py-3 text-sm shadow-xl ${t.type === 'error' ? 'border-red-700 bg-red-950 text-red-100' : 'border-emerald-700 bg-emerald-950 text-emerald-100'}`}>
            {t.type === 'error' ? <XCircle size={18} className="mt-0.5 shrink-0" /> : <CheckCircle2 size={18} className="mt-0.5 shrink-0" />}
            <span className="whitespace-pre-line">{t.message}</span>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  )
}
