import { useState } from 'react'
import { motion } from 'framer-motion'
import { useVault } from '../hooks/useVault'
import VaultLayout from '../components/VaultLayout'

function PasswordField({
  value,
  onChange,
  placeholder,
  autoComplete,
  showPassword,
  onToggleShow,
}: {
  value: string
  onChange: (v: string) => void
  placeholder: string
  autoComplete: string
  showPassword: boolean
  onToggleShow: () => void
}) {
  return (
    <div className="relative">
      <input
        type={showPassword ? 'text' : 'password'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-2 pr-12 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)]"
        placeholder={placeholder}
        autoComplete={autoComplete}
      />
      <button
        type="button"
        onClick={onToggleShow}
        className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded text-[var(--color-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface)] transition-colors"
        title={showPassword ? 'Hide password' : 'Show password'}
        aria-label={showPassword ? 'Hide password' : 'Show password'}
      >
        {showPassword ? (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" /></svg>
        ) : (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
        )}
      </button>
    </div>
  )
}

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
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [showUnlockPassword, setShowUnlockPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (loading || !status) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)]">
        <motion.div className="animate-pulse text-[var(--color-muted)]" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>Loading vault…</motion.div>
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
      <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--color-bg)] px-4 relative">
        <div className="vault-bg-gradient" aria-hidden />
        <motion.div className="w-full max-w-md relative z-10" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, ease: 'easeInOut' }}>
          <h1 className="text-2xl font-semibold text-[var(--color-text)] mb-2">Create New Vault</h1>
          <p className="text-[var(--color-muted)] text-sm mb-6">
            Set a password to protect your encrypted documents. You will need this password to unlock the vault.
          </p>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Password</label>
              <PasswordField
                value={password}
                onChange={setPassword}
                placeholder="At least 8 characters"
                autoComplete="new-password"
                showPassword={showPassword}
                onToggleShow={() => setShowPassword((v) => !v)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Confirm password</label>
              <PasswordField
                value={confirmPassword}
                onChange={setConfirmPassword}
                placeholder="Confirm password"
                autoComplete="new-password"
                showPassword={showConfirmPassword}
                onToggleShow={() => setShowConfirmPassword((v) => !v)}
              />
            </div>
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <motion.button type="submit" disabled={submitting} className="w-full py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium disabled:opacity-50 transition-shadow duration-200 hover:shadow-[0_0_16px_rgba(139,92,246,0.35)]" whileHover={!submitting ? { scale: 1.02 } : undefined} whileTap={{ scale: 0.98 }}>
              {submitting ? 'Creating…' : 'Create vault'}
            </motion.button>
          </form>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--color-bg)] px-4 relative">
      <div className="vault-bg-gradient" aria-hidden />
      <motion.div className="w-full max-w-md relative z-10" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, ease: 'easeInOut' }}>
        <h1 className="text-2xl font-semibold text-[var(--color-text)] mb-2">Unlock vault</h1>
        <p className="text-[var(--color-muted)] text-sm mb-6">
          Enter your vault password to access your documents.
        </p>
        <form onSubmit={handleUnlock} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Password</label>
            <PasswordField
              value={unlockPassword}
              onChange={setUnlockPassword}
              placeholder="Vault password"
              autoComplete="current-password"
              showPassword={showUnlockPassword}
              onToggleShow={() => setShowUnlockPassword((v) => !v)}
            />
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <motion.button type="submit" disabled={submitting} className="w-full py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium disabled:opacity-50 transition-shadow duration-200 hover:shadow-[0_0_16px_rgba(139,92,246,0.35)]" whileHover={!submitting ? { scale: 1.02 } : undefined} whileTap={{ scale: 0.98 }}>
            {submitting ? 'Unlocking…' : 'Unlock vault'}
          </motion.button>
        </form>
      </motion.div>
    </div>
  )
}
