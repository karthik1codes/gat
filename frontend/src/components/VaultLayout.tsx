import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useVault } from '../hooks/useVault'
import Dashboard from '../pages/Dashboard'

export default function VaultLayout() {
  const { user, logout } = useAuth()
  const { status, stats, lock } = useVault()
  const navigate = useNavigate()

  const handleLock = async () => {
    await lock()
    navigate(0) // reload to show VaultGate unlock screen
  }

  const vaultName = user?.name || user?.email || 'My Vault'
  const vaultPath = 'My documents'

  return (
    <div className="min-h-screen flex bg-[var(--color-bg)]">
      {/* Left sidebar - vault list and actions */}
      <aside className="w-56 flex flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)]/50">
        <div className="p-4 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-2">
            <span className="text-lg font-medium text-[var(--color-text)] truncate">{vaultName}</span>
            <svg className="w-4 h-4 text-green-500 shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden>
              <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
            </svg>
          </div>
          <p className="text-xs text-[var(--color-muted)] mt-0.5 truncate">{vaultPath}</p>
        </div>

        <div className="flex-1 p-4 flex flex-col">
          <div className="mb-4">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-500/20 text-green-600 dark:text-green-400">
              UNLOCKED
            </span>
          </div>
          <button
            type="button"
            onClick={() => document.getElementById('documents')?.scrollIntoView({ behavior: 'smooth' })}
            className="w-full flex flex-col items-center justify-center py-4 px-3 rounded-xl bg-[var(--color-primary)] text-white font-medium hover:opacity-90 transition mb-3"
          >
            <svg className="w-8 h-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
            </svg>
            Reveal Drive
            <span className="text-xs opacity-90 mt-1">Documents</span>
          </button>
          <button
            type="button"
            onClick={handleLock}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] hover:bg-[var(--color-surface)] transition"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            Lock
          </button>
        </div>

        {/* Bottom actions - match reference UI */}
        <div className="p-2 border-t border-[var(--color-border)] flex gap-2">
          <button type="button" className="p-2 rounded-lg text-[var(--color-muted)] hover:bg-[var(--color-bg)] hover:text-[var(--color-text)]" title="Add vault (one per account)">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
          </button>
          <button type="button" className="p-2 rounded-lg text-[var(--color-muted)] hover:bg-[var(--color-bg)] hover:text-[var(--color-text)]" title="Notifications">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>
          </button>
          <button type="button" className="p-2 rounded-lg text-[var(--color-muted)] hover:bg-[var(--color-bg)] hover:text-[var(--color-text)]" title="Settings">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
          </button>
        </div>

        {/* Vault Statistics */}
        <div className="p-4 border-t border-[var(--color-border)]">
          <h3 className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wider mb-2">Vault Statistics</h3>
          {stats ? (
            <div className="space-y-1.5 text-sm text-[var(--color-text)]">
              <p>Files: {stats.total_encrypted_files}</p>
              <p>Size: {(stats.total_encrypted_size_bytes / 1024).toFixed(1)} KB</p>
              <p>Index: {(stats.index_size_bytes / 1024).toFixed(1)} KB</p>
              <p className="text-[var(--color-muted)] text-xs pt-1">{stats.encryption_algorithm} · {stats.kdf_algorithm}</p>
            </div>
          ) : (
            <p className="text-[var(--color-muted)] text-sm">—</p>
          )}
        </div>
      </aside>

      {/* Main: header + vault message + dashboard */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="border-b border-[var(--color-border)] bg-[var(--color-surface)]/80 backdrop-blur shrink-0">
          <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
            <a href="/" className="font-semibold text-[var(--color-text)]">
              SSE
            </a>
            <div className="flex items-center gap-4">
              <span className="text-sm text-[var(--color-muted)] truncate max-w-[180px]">{user?.email}</span>
              {user?.picture && (
                <img src={user.picture} alt="" className="w-8 h-8 rounded-full border border-[var(--color-border)]" />
              )}
              <button
                type="button"
                onClick={logout}
                className="text-sm text-[var(--color-muted)] hover:text-[var(--color-text)] transition"
              >
                Sign out
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8">
          <div className="mb-8">
            <p className="text-[var(--color-muted)] mb-4">Your vault's contents are accessible here:</p>
            <button
              type="button"
              onClick={() => document.getElementById('documents')?.scrollIntoView({ behavior: 'smooth' })}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium hover:opacity-90"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
              </svg>
              Reveal Drive
            </button>
            <button
              type="button"
              onClick={handleLock}
              className="ml-3 inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] hover:bg-[var(--color-surface)]"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              Lock
            </button>
          </div>

          <div id="documents">
            <Dashboard />
          </div>
        </main>
      </div>
    </div>
  )
}
