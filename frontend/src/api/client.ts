import axios from 'axios'

export const TOKEN_STORAGE_KEY = 'ders_forumu_token'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor: localStorage'taki token'ı Authorization header'ına ekle.
client.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY)
  if (token) {
    config.headers = config.headers ?? {}
    ;(config.headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
  }
  return config
})

// Response interceptor: 401 dönerse token'ı temizle (UI auth context yenilesin).
client.interceptors.response.use(
  (resp) => resp,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      // Sayfa yenilemesi yerine custom event — AuthContext dinleyebilir.
      window.dispatchEvent(new Event('auth:unauthorized'))
    }
    return Promise.reject(error)
  },
)

export default client
