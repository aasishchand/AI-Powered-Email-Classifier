import axios from 'axios'

/** FastAPI lives under `/api/v1`. If env is `http://localhost:8000` only, requests would 404 on `/pipeline/...`. */
function resolveApiBase(): string {
  const raw = (import.meta.env.VITE_API_URL || '').trim()
  if (!raw) return '/api/v1'
  const base = raw.replace(/\/+$/, '')
  if (base === '/api/v1' || base.endsWith('/api/v1')) return base
  if (base.startsWith('http://') || base.startsWith('https://')) return `${base}/api/v1`
  return base.startsWith('/') ? base : `/${base}`
}

const baseURL = resolveApiBase()

export const api = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const isLoginRequest = err.config?.url?.includes('auth/login')
    if (err.response?.status === 401 && !isLoginRequest) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_email')
      localStorage.removeItem('user_full_name')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)
