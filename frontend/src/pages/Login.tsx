import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google'
import { useAuth } from '../hooks/useAuth'
import { authApi, API_BASE } from '../api/client'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

function LoginContent() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [backendOk, setBackendOk] = useState<boolean | null>(null)

  useEffect(() => {
    let cancelled = false
    fetch(`${API_BASE}/api/health`)
      .then((r) => { if (!cancelled) setBackendOk(r.ok) })
      .catch(() => { if (!cancelled) setBackendOk(false) })
    return () => { cancelled = true }
  }, [])

  const handleGoogleSuccess = async (credentialResponse: { credential?: string }) => {
    const idToken = credentialResponse.credential
    if (!idToken) return
    try {
      const { access_token, user: userFromBackend } = await authApi.google(idToken)
      login(access_token, userFromBackend)
      navigate('/', { replace: true })
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Login failed.'
      if (msg.includes('Failed to fetch') || msg.includes('Not Found')) {
        alert('Backend not reachable. Start it with: uvicorn backend.app.main:app --reload --port 8000')
      } else {
        alert(msg)
      }
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--color-bg)] px-4 relative">
      <div className="vault-bg-gradient" aria-hidden />
      <motion.div
        className="w-full max-w-md text-center relative z-10"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeInOut' }}
      >
        <h1 className="text-3xl font-semibold tracking-tight text-[var(--color-text)] mb-2">
          Secured String Matching
        </h1>
        <p className="text-[var(--color-muted)] mb-8">
          Search on encrypted data without revealing it.
        </p>
        {backendOk === false && (
          <motion.div className="mb-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-200 text-sm" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            Backend not reachable. Start it: <code className="block mt-1 font-mono text-xs">uvicorn backend.app.main:app --reload --port 8000</code>
          </motion.div>
        )}
        <motion.div
          className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-8 shadow-xl transition-shadow duration-200 hover:shadow-[0_8px_30px_rgba(0,0,0,0.3)]"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.05 }}
        >
          {GOOGLE_CLIENT_ID ? (
            <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
              <div className="flex justify-center">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={() => alert('Sign-in failed. In Google Cloud Console → Credentials → your OAuth client, add Authorized JavaScript origin: http://localhost:5173')}
                  useOneTap={false}
                  theme="filled_black"
                  size="large"
                  text="continue_with"
                  shape="rectangular"
                />
              </div>
            </GoogleOAuthProvider>
          ) : (
            <p className="text-[var(--color-muted)] text-sm">
              Add VITE_GOOGLE_CLIENT_ID to frontend .env and restart the dev server.
            </p>
          )}
        </motion.div>
      </motion.div>
    </div>
  )
}

export default function Login() {
  return <LoginContent />
}
