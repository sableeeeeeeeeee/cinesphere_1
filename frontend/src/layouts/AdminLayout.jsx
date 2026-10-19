import { useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { BarChart3, Building2, CalendarClock, ChevronLeft, ChevronRight, Film, Flag, History, Popcorn, ScanLine, Tag, Ticket, Users } from 'lucide-react'
import { Logo } from '../components/Navbar'
import { useAuth } from '../context/AuthContext'

const ITEMS = [
  ['/admin', 'Dashboard', BarChart3, true, ['admin', 'staff']], ['/admin/movies', 'Movies', Film, false, ['admin']],
  ['/admin/cinemas', 'Cinemas & screens', Building2, false, ['admin']], ['/admin/shows', 'Showtimes', CalendarClock, false, ['admin']],
  ['/admin/bookings', 'Bookings', Ticket, false, ['admin']], ['/admin/validate', 'Validate ticket', ScanLine, false, ['admin', 'staff']],
  ['/admin/food', 'Food', Popcorn, false, ['admin', 'staff']], ['/admin/reviews', 'Review reports', Flag, false, ['admin']],
  ['/admin/coupons', 'Coupons', Tag, false, ['admin']], ['/admin/users', 'Users', Users, false, ['admin']], ['/admin/audit', 'Audit log', History, false, ['admin']],
]

export default function AdminLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const { user } = useAuth()
  return (
    <div className="flex min-h-screen">
      <aside className={`sticky top-0 h-screen shrink-0 border-r border-edge bg-panel transition-all ${collapsed ? 'w-16' : 'w-60'}`}>
        <div className="flex items-center justify-between p-3">{!collapsed && <Link to="/"><Logo className="!text-2xl" /></Link>}
          <button className="btn-ghost !p-2" aria-label="Toggle sidebar" onClick={() => setCollapsed(!collapsed)}>{collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}</button></div>
        <nav className="space-y-1 p-2" aria-label="Admin">
          {ITEMS.filter((i) => i[4].includes(user.role)).map(([to, label, Icon, end]) => (
            <NavLink key={to} to={to} end={end} title={label} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm ${isActive ? 'bg-brand text-white' : 'text-slate-300 hover:bg-ink'}`}>
              <Icon size={18} className="shrink-0" />{!collapsed && label}</NavLink>))}
        </nav>
      </aside>
      <main className="min-w-0 flex-1 p-6"><Outlet /></main>
    </div>
  )
}
