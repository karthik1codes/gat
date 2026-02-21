import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { authApi } from '../api/client'

type User = { id: string; email: string; name: string | null; picture: string | null } | null

const AuthContext = createContext<{
  user: User
  loading: boolean
  login: (accessToken: string) => void
  logout: () => void
  refreshUser: () => Promise<void>
} | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const u = await authApi.me()
      setUser(u)
    } catch {
      localStorage.removeItem('access_token')
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshUser()
  }, [refreshUser])

  const login = useCallback((accessToken: string, userFromBackend?: User) => {
    localStorage.setItem('access_token', accessToken)
    if (userFromBackend) {
      setUser(userFromBackend)
      setLoading(false)
    }
    refreshUser()
  }, [refreshUser])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
