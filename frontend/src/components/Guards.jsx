import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Spinner } from './ui'

// UI-level convenience only. The backend enforces every permission independently.
export function RequireAuth({ roles }) {
  const { user, loading } = useAuth()
  const loc = useLocation()
  if (loading) return <Spinner />
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname + loc.search }} replace />
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />
  return <Outlet />
}
