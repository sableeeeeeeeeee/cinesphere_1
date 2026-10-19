import { Navigate, Route, Routes } from 'react-router-dom'
import CustomerLayout from './layouts/CustomerLayout'
import AdminLayout from './layouts/AdminLayout'
import { RequireAuth } from './components/Guards'
import Home from './pages/Home'
import MovieDetail from './pages/MovieDetail'
import SeatSelection from './pages/SeatSelection'
import Checkout from './pages/Checkout'
import { MyBookings, Ticket } from './pages/Bookings'
import Food from './pages/Food'
import Profile from './pages/Profile'
import { Forgot, Login, Register, Reset } from './pages/AuthPages'
import Dashboard from './pages/admin/Dashboard'
import { AdminMovies, AdminShows, AdminBookings, AdminFood, AdminReviews, AdminUsers, AdminCoupons, AdminAudit, ValidateTicket } from './pages/admin/Modules'
import Cinemas from './pages/admin/Cinemas'
import ScreenEditor from './pages/admin/ScreenEditor'

export default function App() {
  return (
    <Routes>
      <Route element={<CustomerLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/movies/:id" element={<MovieDetail />} />
        <Route path="/shows/:showId/seats" element={<SeatSelection />} />
        <Route path="/food" element={<Food />} />
        <Route path="/login" element={<Login />} /><Route path="/register" element={<Register />} />
        <Route path="/forgot" element={<Forgot />} /><Route path="/reset" element={<Reset />} />
        <Route element={<RequireAuth />}>
          <Route path="/checkout/:showId" element={<Checkout />} />
          <Route path="/bookings" element={<MyBookings />} /><Route path="/bookings/:id" element={<Ticket />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
      </Route>
      <Route element={<RequireAuth roles={['admin', 'staff']} />}>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="validate" element={<ValidateTicket />} />
          <Route path="food" element={<AdminFood />} />
          <Route element={<RequireAuth roles={['admin']} />}>
            <Route path="movies" element={<AdminMovies />} />
            <Route path="cinemas" element={<Cinemas />} />
            <Route path="screens/:id" element={<ScreenEditor />} />
            <Route path="shows" element={<AdminShows />} />
            <Route path="bookings" element={<AdminBookings />} />
            <Route path="reviews" element={<AdminReviews />} />
            <Route path="users" element={<AdminUsers />} />
            <Route path="coupons" element={<AdminCoupons />} />
            <Route path="audit" element={<AdminAudit />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
