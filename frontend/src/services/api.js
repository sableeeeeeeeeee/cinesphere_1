import axios from 'axios'

// Access token lives in memory only; the refresh token is an httpOnly cookie set by the backend.
let accessToken = null
let onAuthLost = () => {}
export const setAccessToken = (t) => { accessToken = t }
export const setAuthLostHandler = (fn) => { onAuthLost = fn }

const api = axios.create({ baseURL: '/api', withCredentials: true })

api.interceptors.request.use((cfg) => {
  if (accessToken) cfg.headers.Authorization = `Bearer ${accessToken}`
  return cfg
})

let refreshing = null
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const { config, response } = err
    const isAuthCall = config?.url?.startsWith('/auth/')
    if (response?.status === 401 && !config._retried && !isAuthCall && accessToken) {
      config._retried = true
      try {
        refreshing = refreshing || api.post('/auth/refresh').finally(() => { refreshing = null })
        const { data } = await refreshing
        accessToken = data.access_token
        return api(config)
      } catch {
        accessToken = null
        onAuthLost()
      }
    }
    return Promise.reject(err)
  },
)

/** Turn any API error into a readable string, plus the machine-readable code and seat ids when present. */
export function errInfo(e) {
  const d = e?.response?.data
  let message = 'Something went wrong. Please try again.'
  if (typeof d?.detail === 'string') message = d.detail
  else if (d?.detail?.message) message = [d.detail.message, ...(d.detail.errors || [])].join('\n')
  else if (Array.isArray(d?.detail)) message = d.detail.map((x) => `${(x.loc || []).slice(1).join('.')}: ${x.msg}`).join('\n')
  else if (!e?.response) message = 'Cannot reach the server. Is the backend running?'
  return { message, code: d?.code, seatIds: d?.seat_ids || [], status: e?.response?.status }
}

export default api
