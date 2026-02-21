import { useState, useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useVault } from '../hooks/useVault'
import type { VaultListItem } from '../api/client'

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
 * When no vaults: show Create New Vault (name + password + confirm).
 * When vaults exist but locked: show Create New Vault + Open Existing Vault (list, select, password).
 * When vault unlocked: show main app (VaultLayout + dashboard).
 */
export default function VaultGate() {
  const { status, loading, createVault, unlock, listVaults } = useVault()
  const [vaultName, setVaultName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [unlockPassword, setUnlockPassword] = useState('')
  const [vaultList, setVaultList] = useState<VaultListItem[]>([])
  const [selectedVaultId, setSelectedVaultId] = useState<string | null>(null)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [showUnlockPassword, setShowUnlockPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [mode, setMode] = useState<'choose' | 'create' | 'open'>('choose')

  useEffect(() => {
    if (status?.initialized) listVaults().then(setVaultList).catch(() => setVaultList([]))
  }, [status?.initialized, listVaults])

  if (loading || !status) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)]">
        <motion.div className="animate-pulse text-[var(--color-muted)]" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>Loading vault…</motion.div>
      </div>
    )
  }

  if (status.initialized && status.state === 'UNLOCKED') {
    return <Outlet />
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const name = (vaultName || '').trim()
    if (!name) {
      setError('Vault name is required')
      return
    }
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
      await createVault(name, password)
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
    const vaultId = selectedVaultId || undefined
    if (vaultList.length > 0 && !vaultId) {
      setError('Select a vault to open')
      return
    }
    setSubmitting(true)
    try {
      await unlock(unlockPassword, vaultId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid password')
    } finally {
      setSubmitting(false)
    }
  }

  // No vaults yet: only Create New Vault
  if (!status.initialized) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--color-bg)] px-4 relative">
        <div className="vault-bg-gradient" aria-hidden />
        <motion.div className="w-full max-w-md relative z-10" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, ease: 'easeInOut' }}>
          <h1 className="text-2xl font-semibold text-[var(--color-text)] mb-2">Create New Vault</h1>
          <p className="text-[var(--color-muted)] text-sm mb-6">
            Set a name and password to protect your encrypted documents. You will need this password to unlock the vault.
          </p>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Vault name</label>
              <input
                type="text"
                value={vaultName}
                onChange={(e) => setVaultName(e.target.value)}
                className="w-full px-4 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)]"
                placeholder="e.g. Personal"
                autoComplete="off"
              />
            </div>
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

  // Has vaults but locked: Choose Create New / Open Existing
  if (mode === 'create') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--color-bg)] px-4 relative">
        <div className="vault-bg-gradient" aria-hidden />
        <motion.div className="w-full max-w-md relative z-10" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, ease: 'easeInOut' }}>
          <button type="button" onClick={() => setMode('choose')} className="text-sm text-[var(--color-muted)] hover:text-[var(--color-text)] mb-4">← Back</button>
          <h1 className="text-2xl font-semibold text-[var(--color-text)] mb-2">Create New Vault</h1>
          <p className="text-[var(--color-muted)] text-sm mb-6">Set a name and password for the new vault.</p>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Vault name</label>
              <input
                type="text"
                value={vaultName}
                onChange={(e) => setVaultName(e.target.value)}
                className="w-full px-4 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)]"
                placeholder="e.g. Work"
                autoComplete="off"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Password</label>
              <PasswordField value={password} onChange={setPassword} placeholder="At least 8 characters" autoComplete="new-password" showPassword={showPassword} onToggleShow={() => setShowPassword((v) => !v)} />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Confirm password</label>
              <PasswordField value={confirmPassword} onChange={setConfirmPassword} placeholder="Confirm password" autoComplete="new-password" showPassword={showConfirmPassword} onToggleShow={() => setShowConfirmPassword((v) => !v)} />
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

  if (mode === 'open') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--color-bg)] px-4 relative">
        <div className="vault-bg-gradient" aria-hidden />
        <motion.div className="w-full max-w-md relative z-10" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, ease: 'easeInOut' }}>
          <button type="button" onClick={() => setMode('choose')} className="text-sm text-[var(--color-muted)] hover:text-[var(--color-text)] mb-4">← Back</button>
          <h1 className="text-2xl font-semibold text-[var(--color-text)] mb-2">Open Existing Vault</h1>
          <p className="text-[var(--color-muted)] text-sm mb-6">Select a vault and enter its password.</p>
          <form onSubmit={handleUnlock} className="space-y-4">
            {vaultList.length > 0 && (
              <div className="space-y-1">
                <label htmlFor="vault-select" className="block text-sm font-medium text-[var(--color-text)]">Vault</label>
                <select
                  id="vault-select"
                  value={selectedVaultId ?? ''}
                  onChange={(e) => setSelectedVaultId(e.target.value || null)}
                  className="block w-full min-h-[42px] pl-4 pr-10 py-2.5 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] appearance-none cursor-pointer bg-no-repeat bg-[length:1.25rem] bg-[right_0.75rem_center]"
                  style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%239ca3af'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E\")" }}
                >
                  <option value="">Select a vault…</option>
                  {vaultList.map((v) => (
                    <option key={v.id} value={v.id}>{v.name}</option>
                  ))}
                </select>
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Password</label>
              <PasswordField value={unlockPassword} onChange={setUnlockPassword} placeholder="Vault password" autoComplete="current-password" showPassword={showUnlockPassword} onToggleShow={() => setShowUnlockPassword((v) => !v)} />
            </div>
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <motion.button type="submit" disabled={submitting} className="w-full py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium disabled:opacity-50 transition-shadow duration-200 hover:shadow-[0_0_16px_rgba(139,92,246,0.35)]" whileHover={!submitting ? { scale: 1.02 } : undefined} whileTap={{ scale: 0.98 }}>
              {submitting ? 'Unlocking…' : 'Open vault'}
            </motion.button>
          </form>
        </motion.div>
      </div>
    )
  }

  // mode === 'choose': show Create New Vault / Open Existing Vault
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--color-bg)] px-4 relative">
      <div className="vault-bg-gradient" aria-hidden />
      <motion.div className="w-full max-w-md relative z-10" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, ease: 'easeInOut' }}>
        <h1 className="text-2xl font-semibold text-[var(--color-text)] mb-2">Vault</h1>
        <p className="text-[var(--color-muted)] text-sm mb-6">Create a new vault or open an existing one.</p>
        <div className="space-y-3">
          <motion.button
            type="button"
            onClick={() => setMode('create')}
            className="w-full flex items-center gap-3 py-3 px-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] hover:bg-[var(--color-bg)] transition-colors"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <span className="text-xl">+</span>
            <span>Create New Vault…</span>
          </motion.button>
          <motion.button
            type="button"
            onClick={() => { setMode('open'); setSelectedVaultId(vaultList[0]?.id ?? null); }}
            className="w-full flex items-center gap-3 py-3 px-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] hover:bg-[var(--color-bg)] transition-colors"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <svg className="w-5 h-5 text-[var(--color-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>
            <span>Open Existing Vault…</span>
          </motion.button>
        </div>
      </motion.div>
    </div>
  )
}
