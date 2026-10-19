import { useEffect, useRef, useState } from 'react'

// One id per browser tab. Two tabs of the same account are treated as two separate customers by the backend.
export function getSessionId() {
  let s = sessionStorage.getItem('cv_session')
  if (!s) { s = (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2) + Date.now()).replace(/-/g, ''); sessionStorage.setItem('cv_session', s) }
  return s
}

/** Counts down from the server-reported remaining seconds (never from the client clock alone). */
export function useCountdown(secondsRemaining, onZero) {
  const [left, setLeft] = useState(secondsRemaining || 0)
  const target = useRef(0)
  const cb = useRef(onZero)
  cb.current = onZero
  useEffect(() => { target.current = Date.now() + (secondsRemaining || 0) * 1000; setLeft(secondsRemaining || 0) }, [secondsRemaining])
  useEffect(() => {
    const t = setInterval(() => {
      const s = Math.max(0, Math.round((target.current - Date.now()) / 1000))
      setLeft((prev) => { if (prev > 0 && s === 0) setTimeout(() => cb.current?.(), 0); return s })
    }, 500)
    return () => clearInterval(t)
  }, [])
  return left
}
export const mmss = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
