import { useEffect, useState } from 'react'

// City choice is remembered in localStorage (a harmless per-device preference).
export function useCity() {
  const [city, setCityState] = useState(() => localStorage.getItem('cv_city') || '')
  const setCity = (c) => { localStorage.setItem('cv_city', c); setCityState(c) }
  return [city, setCity]
}

export function pushRecent(id) {
  const list = JSON.parse(localStorage.getItem('cv_recent') || '[]').filter((x) => x !== id)
  localStorage.setItem('cv_recent', JSON.stringify([id, ...list].slice(0, 8)))
}
export const getRecent = () => JSON.parse(localStorage.getItem('cv_recent') || '[]')
