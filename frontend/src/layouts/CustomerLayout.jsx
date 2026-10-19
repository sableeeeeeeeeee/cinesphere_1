import { Link, Outlet } from 'react-router-dom'
import Navbar, { Logo } from '../components/Navbar'

export default function CustomerLayout() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8"><Outlet /></main>
      <footer className="mt-10 border-t border-edge bg-panel/60">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-8 text-sm text-slate-400">
          <div className="space-y-2"><Logo className="!text-lg" /><p className="max-w-sm text-xs">Book movie tickets, choose your seats and pre-order food. Demo project: payments are simulated.</p></div>
          <nav className="flex gap-6" aria-label="Footer"><Link to="/" className="hover:text-white">Movies</Link><Link to="/food" className="hover:text-white">Food &amp; drinks</Link><Link to="/bookings" className="hover:text-white">My bookings</Link></nav>
        </div>
      </footer>
    </div>
  )
}
