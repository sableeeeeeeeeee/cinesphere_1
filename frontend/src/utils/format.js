export const money = (paise) => `₹${((paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`
export const fmtTime = (iso) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
export const fmtDate = (iso) => new Date(iso).toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short' })
export const fmtDateTime = (iso) => `${fmtDate(iso)}, ${fmtTime(iso)}`
export const tzOffset = () => -new Date().getTimezoneOffset() // minutes east of UTC, what /shows?tz= expects
export const localDateStr = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
export const uid = () => (crypto.randomUUID ? crypto.randomUUID().replace(/-/g, '') : String(Math.random()).slice(2) + Date.now())
export const CATEGORY_STYLES = {
  standard: 'bg-slate-600 text-white', premium: 'bg-sky-600 text-white', executive: 'bg-emerald-600 text-white',
  recliner: 'bg-amber-600 text-white', balcony: 'bg-fuchsia-700 text-white', wheelchair: 'bg-teal-500 text-slate-900', companion: 'bg-teal-800 text-white',
}
export const CATEGORIES = Object.keys(CATEGORY_STYLES)
