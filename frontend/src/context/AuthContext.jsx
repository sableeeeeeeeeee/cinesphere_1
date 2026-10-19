import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import api, { setAccessToken, setAuthLostHandler } from '../services/api'

const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const accept = useCallback((data) => { setAccessToken(data.access_token); setUser(data.user); return data.user }, [])

  // Session persistence: on page load, trade the httpOnly refresh cookie for a fresh access token.
  useEffect(() => {
    setAuthLostHandler(() => setUser(null))
    api.post('/auth/refresh').then((r) => accept(r.data)).catch(() => {}).finally(() => setLoading(false))
  }, [accept])

  const login = async (email, password) => accept((await api.post('/auth/login', { email, password })).data)
  const register = async (form) => accept((await api.post('/auth/register', form)).data)
  const logout = async () => { await api.post('/auth/logout').catch(() => {}); setAccessToken(null); setUser(null) }

  return <AuthCtx.Provider value={{ user, setUser, loading, login, register, logout }}>{children}</AuthCtx.Provider>
}
