import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { AuthUser } from '../api'
import * as api from '../api'
import { TOKEN_STORAGE_KEY } from '../api/client'

interface AuthState {
  user: AuthUser | null
  loading: boolean
  login: (identifier: string, password: string) => Promise<void>
  // Register iki adımlıdır — start → verify
  registerStart: (data: api.RegisterStartPayload) => Promise<api.RegisterStartResponse>
  registerVerify: (email: string, otp: string) => Promise<void>
  refreshUser: () => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  // İlk açılışta token varsa /me ile kullanıcıyı doğrula
  useEffect(() => {
    let cancelled = false
    const onUnauth = () => { setUser(null) }
    window.addEventListener('auth:unauthorized', onUnauth)

    const token = localStorage.getItem(TOKEN_STORAGE_KEY)
    if (!token) {
      setLoading(false)
      return () => {
        cancelled = true
        window.removeEventListener('auth:unauthorized', onUnauth)
      }
    }
    api.getMe()
      .then((u) => { if (!cancelled) setUser(u) })
      .catch(() => {
        localStorage.removeItem(TOKEN_STORAGE_KEY)
        if (!cancelled) setUser(null)
      })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => {
      cancelled = true
      window.removeEventListener('auth:unauthorized', onUnauth)
    }
  }, [])

  const setSession = useCallback((token: string, u: AuthUser) => {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
    setUser(u)
  }, [])

  const refreshUser = useCallback(async () => {
    const next = await api.getMe()
    setUser(next)
  }, [])

  const login = useCallback(async (identifier: string, password: string) => {
    const resp = await api.login({ identifier, password })
    setSession(resp.access_token, resp.user)
  }, [setSession])

  const registerStart = useCallback(async (data: api.RegisterStartPayload) => {
    return api.registerStart(data)
  }, [])

  const registerVerify = useCallback(async (email: string, otp: string) => {
    const resp = await api.registerVerify({ email, otp })
    setSession(resp.access_token, resp.user)
  }, [setSession])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    setUser(null)
  }, [])

  const value = useMemo<AuthState>(() => ({
    user, loading, login, registerStart, registerVerify, refreshUser, logout,
  }), [user, loading, login, registerStart, registerVerify, refreshUser, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
