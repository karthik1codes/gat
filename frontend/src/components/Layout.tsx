import { Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      <header className="border-b border-[var(--color-border)] bg-[var(--color-surface)]/80 backdrop-blur">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          <a href="/" className="font-semibold text-[var(--color-text)]">
            SSE
          </a>
          <div className="flex items-center gap-4">
            <span className="text-sm text-[var(--color-muted)] truncate max-w-[180px]">
              {user?.email}
            </span>
            {user?.picture && (
              <img
                src={user.picture}
                alt=""
                className="w-8 h-8 rounded-full border border-[var(--color-border)]"
              />
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
      <main className="max-w-5xl mx-auto px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
