import { useState } from 'react'
import { useVault } from '../hooks/useVault'
import VaultLayout from '../components/VaultLayout'

/**
 * When vault is not initialized: show Create New Vault (password + confirm).
 * When vault is locked: show Unlock vault (password).
 * When vault is unlocked: show main app (VaultLayout + dashboard).
 */
export default function VaultGate() {
  const { status, loading, createVault, unlock } = useVault()
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [unlockPassword, setUnlockPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (loading || !status) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)]">
        <div className="animate-pulse text-[var(--color-muted)]">Loading vault…</div>
      </div>
    )
  }

  if (status.initialized && status.state === 'UNLOCKED') {
    return <VaultLayout />
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    setSubmitting(true)
    try {
      await createVault(password)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create vault')
    } finally {
      setSubmitting(false)
    }
  }

  const handleUnlock = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!unlockPassword.trim()) return
    setSubmitting(true)
    try {
      await unlock(unlockPassword)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid password')
    } finally {
      setSubmitting(false)
    }
  }

  if (!status.initialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)] px-4">
        <div className="w-full max-w-md">
          <h1 className="text-2xl font-semibold text-[var(--color-text)] mb-2">Create New Vault</h1>
          <p className="text-[var(--color-muted)] text-sm mb-6">
            Set a password to protect your encrypted documents. You will need this password to unlock the vault.
          </p>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)]"
                placeholder="At least 8 characters"
                autoComplete="new-password"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Confirm password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-4 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)]"
                placeholder="Confirm password"
                autoComplete="new-password"
              />
            </div>
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium disabled:opacity-50"
            >
              {submitting ? 'Creating…' : 'Create vault'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)] px-4">
      <div className="w-full max-w-md">
        <h1 className="text-2xl font-semibold text-[var(--color-text)] mb-2">Unlock vault</h1>
        <p className="text-[var(--color-muted)] text-sm mb-6">
          Enter your vault password to access your documents.
        </p>
        <form onSubmit={handleUnlock} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Password</label>
            <input
              type="password"
              value={unlockPassword}
              onChange={(e) => setUnlockPassword(e.target.value)}
              className="w-full px-4 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)]"
              placeholder="Vault password"
              autoComplete="current-password"
            />
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium disabled:opacity-50"
          >
            {submitting ? 'Unlocking…' : 'Unlock vault'}
          </button>
        </form>
      </div>
    </div>
  )
}
