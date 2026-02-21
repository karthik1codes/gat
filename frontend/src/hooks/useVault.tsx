import { createContext, useContext, useCallback, useEffect, useState } from 'react'
import { vaultApi, type VaultStatus, type VaultStats } from '../api/client'

type VaultContextValue = {
  status: VaultStatus | null
  stats: VaultStats | null
  loading: boolean
  refresh: () => Promise<void>
  unlock: (password: string) => Promise<void>
  lock: () => Promise<void>
  createVault: (password: string) => Promise<void>
}

const VaultContext = createContext<VaultContextValue | null>(null)

export function VaultProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<VaultStatus | null>(null)
  const [stats, setStats] = useState<VaultStats | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const s = await vaultApi.status()
      setStatus(s)
      try {
        const st = await vaultApi.stats()
        setStats(st)
      } catch {
        setStats(null)
      }
    } catch {
      setStatus(null)
      setStats(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const unlock = useCallback(async (password: string) => {
    await vaultApi.unlock(password)
    await refresh()
  }, [refresh])

  const lock = useCallback(async () => {
    await vaultApi.lock()
    await refresh()
  }, [refresh])

  const createVault = useCallback(async (password: string) => {
    await vaultApi.unlock(password) // first unlock creates vault (salt)
    await refresh()
  }, [refresh])

  return (
    <VaultContext.Provider
      value={{
        status,
        stats,
        loading,
        refresh,
        unlock,
        lock,
        createVault,
      }}
    >
      {children}
    </VaultContext.Provider>
  )
}

export function useVault() {
  const ctx = useContext(VaultContext)
  if (!ctx) throw new Error('useVault must be used within VaultProvider')
  return ctx
}
