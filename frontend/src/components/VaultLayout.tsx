import { useState, useEffect } from 'react'
import { useNavigate, Outlet, NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../hooks/useAuth'
import { useVault } from '../hooks/useVault'
import type { VaultListItem } from '../api/client'

const btnHover = { scale: 1.03, transition: { duration: 0.2 } }
const btnTap = { scale: 0.98 }

export default function VaultLayout() {
  const { user, logout } = useAuth()
  const { status, lock, createVault, unlock, listVaults } = useVault()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [openModalOpen, setOpenModalOpen] = useState(false)
  const [vaultList, setVaultList] = useState<VaultListItem[]>([])
  const [createName, setCreateName] = useState('')
  const [createPassword, setCreatePassword] = useState('')
  const [createConfirm, setCreateConfirm] = useState('')
  const [openVaultId, setOpenVaultId] = useState<string | null>(null)
  const [openPassword, setOpenPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    listVaults().then(setVaultList).catch(() => setVaultList([]))
  }, [listVaults, createModalOpen, openModalOpen])

  const handleLock = async () => {
    await lock()
    navigate(0) // reload to show VaultGate unlock screen
  }

  const openCreate = () => { setMenuOpen(false); setCreateModalOpen(true); setError(null); setCreateName(''); setCreatePassword(''); setCreateConfirm(''); }
  const openExisting = () => { setMenuOpen(false); setOpenModalOpen(true); setError(null); setOpenVaultId(vaultList[0]?.id ?? null); setOpenPassword(''); }

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const name = createName.trim()
    if (!name) { setError('Vault name is required'); return }
    if (createPassword.length < 8) { setError('Password must be at least 8 characters'); return }
    if (createPassword !== createConfirm) { setError('Passwords do not match'); return }
    setSubmitting(true)
    try {
      await createVault(name, createPassword)
      setCreateModalOpen(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create vault')
    } finally {
      setSubmitting(false)
    }
  }

  const handleOpenSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!openPassword.trim()) { setError('Password is required'); return }
    const vaultId = vaultList.length > 0 ? (openVaultId || vaultList[0].id) : undefined
    setSubmitting(true)
    try {
      await unlock(openPassword, vaultId)
      setOpenModalOpen(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid password')
    } finally {
      setSubmitting(false)
    }
  }

  const displayName = status?.current_vault_name || user?.name || user?.email || 'Vault'
  const vaultPath = 'My documents'

  return (
    <div className="min-h-screen flex bg-[var(--color-bg)] relative">
      {/* Subtle animated background gradient (20s loop, low opacity) */}
      <div className="vault-bg-gradient" aria-hidden />
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          background: 'radial-gradient(ellipse 100% 80% at 30% 10%, rgba(139,92,246,0.08), transparent 55%), radial-gradient(ellipse 70% 60% at 70% 90%, rgba(34,197,94,0.05), transparent 50%)',
          animation: 'vault-gradient-shift 20s ease-in-out infinite',
        }}
        aria-hidden
      />

      {/* Left sidebar - vault list and actions */}
      <motion.aside
        className="w-56 flex flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)]/80 relative z-10"
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.4 }}
      >
        <div className="p-4 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-2">
            <span className="text-lg font-medium text-[var(--color-text)] truncate">{displayName}</span>
            <svg className="w-4 h-4 text-[var(--color-accent)] shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden>
              <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
            </svg>
          </div>
          <p className="text-xs text-[var(--color-muted)] mt-0.5 truncate">{vaultPath}</p>
        </div>

        <div className="flex-1 p-4 flex flex-col">
          <div className="mb-4">
            <span className="vault-status-unlocked inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[var(--color-accent)]/20 text-[var(--color-accent)]">
              UNLOCKED
            </span>
          </div>
          <NavLink
            to="/"
            className={({ isActive }) =>
              `w-full flex flex-col items-center justify-center py-4 px-3 rounded-xl font-medium mb-3 transition-shadow duration-200 ${isActive ? 'bg-[var(--color-primary)]/80 text-white shadow-[0_0_20px_rgba(139,92,246,0.25)]' : 'bg-[var(--color-primary)] text-white hover:shadow-[0_0_20px_rgba(139,92,246,0.35)]'}`
            }
          >
            <svg className="w-8 h-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
            </svg>
            Documents
            <span className="text-xs opacity-90 mt-1">Upload & search</span>
          </NavLink>
          <NavLink
            to="/performance"
            className={({ isActive }) =>
              `w-full flex flex-col items-center justify-center py-4 px-3 rounded-xl font-medium mb-3 transition-shadow duration-200 ${isActive ? 'bg-[var(--color-primary)]/80 text-white' : 'border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] hover:bg-[var(--color-surface)]'}`
            }
          >
            <svg className="w-8 h-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            Performance
            <span className="text-xs opacity-90 mt-1">Scaling & benchmark</span>
          </NavLink>
          {/* Bottom left: Vault menu */}
          <div className="mt-auto pt-4 pb-2 relative">
            <div className="flex flex-col gap-2">
              <motion.button
                type="button"
                onClick={() => setMenuOpen((o) => !o)}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] hover:bg-[var(--color-surface)] transition-colors duration-200"
                whileHover={btnHover}
                whileTap={btnTap}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
                Vault
              </motion.button>
            </div>
            {menuOpen && (
              <>
                <div className="absolute bottom-full left-0 right-0 mb-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] shadow-lg overflow-hidden z-20">
                  <button
                    type="button"
                    onClick={openCreate}
                    className="w-full flex items-center gap-2 py-2.5 px-3 text-left text-[var(--color-text)] hover:bg-[var(--color-bg)] transition-colors"
                  >
                    <span className="text-[var(--color-primary)]">+</span>
                    Create New Vault…
                  </button>
                  <button
                    type="button"
                    onClick={openExisting}
                    className="w-full flex items-center gap-2 py-2.5 px-3 text-left text-[var(--color-text)] hover:bg-[var(--color-bg)] transition-colors"
                  >
                    <svg className="w-5 h-5 text-[var(--color-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>
                    Open Existing Vault…
                  </button>
                </div>
                <div className="fixed inset-0 z-10" aria-hidden onClick={() => setMenuOpen(false)} />
              </>
            )}
          </div>

          <motion.button
            type="button"
            onClick={handleLock}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] hover:bg-[var(--color-surface)] transition-colors duration-200 mt-2"
            whileHover={btnHover}
            whileTap={btnTap}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            Lock
          </motion.button>
        </div>
      </motion.aside>

      {/* Create New Vault modal */}
      {createModalOpen && (
        <div className="fixed inset-0 z-30 flex items-center justify-center p-4 bg-black/50" onClick={() => !submitting && setCreateModalOpen(false)}>
          <motion.div
            className="bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)] shadow-xl max-w-md w-full p-6"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-[var(--color-text)] mb-4">Create New Vault</h2>
            <form onSubmit={handleCreateSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Vault name</label>
                <input type="text" value={createName} onChange={(e) => setCreateName(e.target.value)} className="w-full px-4 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)]" placeholder="e.g. Work" autoComplete="off" />
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Password</label>
                <input type="password" value={createPassword} onChange={(e) => setCreatePassword(e.target.value)} className="w-full px-4 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)]" placeholder="At least 8 characters" autoComplete="new-password" />
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Confirm password</label>
                <input type="password" value={createConfirm} onChange={(e) => setCreateConfirm(e.target.value)} className="w-full px-4 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)]" placeholder="Confirm password" autoComplete="new-password" />
              </div>
              {error && <p className="text-red-400 text-sm">{error}</p>}
              <div className="flex gap-2 justify-end">
                <button type="button" onClick={() => setCreateModalOpen(false)} className="px-4 py-2 rounded-lg border border-[var(--color-border)] text-[var(--color-text)] hover:bg-[var(--color-bg)]" disabled={submitting}>Cancel</button>
                <button type="submit" disabled={submitting} className="px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white disabled:opacity-50">{submitting ? 'Creating…' : 'Create'}</button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

      {/* Open Existing Vault modal */}
      {openModalOpen && (
        <div className="fixed inset-0 z-30 flex items-center justify-center p-4 bg-black/50" onClick={() => !submitting && setOpenModalOpen(false)}>
          <motion.div
            className="bg-[var(--color-surface)] rounded-xl border border-[var(--color-border)] shadow-xl max-w-md w-full p-6"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-[var(--color-text)] mb-4">Open Existing Vault</h2>
            <form onSubmit={handleOpenSubmit} className="space-y-4">
              {vaultList.length > 0 && (
                <div className="space-y-1">
                  <label htmlFor="open-vault-select" className="block text-sm font-medium text-[var(--color-text)]">Vault</label>
                  <select
                    id="open-vault-select"
                    value={openVaultId ?? ''}
                    onChange={(e) => setOpenVaultId(e.target.value || null)}
                    className="block w-full min-h-[42px] pl-4 pr-10 py-2.5 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] appearance-none cursor-pointer bg-no-repeat bg-[length:1.25rem] bg-[right_0.75rem_center]"
                    style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%239ca3af'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E\")" }}
                  >
                    <option value="">Select…</option>
                    {vaultList.map((v) => (
                      <option key={v.id} value={v.id}>{v.name}</option>
                    ))}
                  </select>
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Password</label>
                <input type="password" value={openPassword} onChange={(e) => setOpenPassword(e.target.value)} className="w-full px-4 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)]" placeholder="Vault password" autoComplete="current-password" />
              </div>
              {error && <p className="text-red-400 text-sm">{error}</p>}
              <div className="flex gap-2 justify-end">
                <button type="button" onClick={() => setOpenModalOpen(false)} className="px-4 py-2 rounded-lg border border-[var(--color-border)] text-[var(--color-text)] hover:bg-[var(--color-bg)]" disabled={submitting}>Cancel</button>
                <button type="submit" disabled={submitting} className="px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white disabled:opacity-50">{submitting ? 'Unlocking…' : 'Open'}</button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

      {/* Main: header + vault message + dashboard */}
      <motion.div className="flex-1 flex flex-col min-w-0 relative z-10 overflow-hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
        {/* Grid cover: subtle gradient overlay so grid is clearly visible */}
        <div className="app-grid-cover" aria-hidden />
        {/* Grid layer: visible line grid on dashboard, performance & scaling */}
        <div className="app-grid-layer" aria-hidden />
        <header className="relative z-10 border-b border-[var(--color-border)] bg-[var(--color-surface)]/80 backdrop-blur shrink-0">
          <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-end">
            <div className="flex items-center gap-4">
              <span className="text-sm text-[var(--color-muted)] truncate max-w-[180px]">{user?.email}</span>
              {user?.picture && (
                <img src={user.picture} alt="" className="w-8 h-8 rounded-full border border-[var(--color-border)]" />
              )}
              <motion.button
                type="button"
                onClick={logout}
                className="text-sm text-[var(--color-muted)] hover:text-[var(--color-text)] transition-colors duration-200"
                whileHover={btnHover}
                whileTap={btnTap}
              >
                Sign out
              </motion.button>
            </div>
          </div>
        </header>

        <main className="relative z-10 flex-1 max-w-4xl w-full mx-auto px-4 py-8">
          <Outlet />
        </main>
      </motion.div>
    </div>
  )
}
