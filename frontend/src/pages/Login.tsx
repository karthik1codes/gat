import { useNavigate } from 'react-router-dom'
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google'
import { useAuth } from '../hooks/useAuth'
import { authApi } from '../api/client'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

function LoginContent() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleGoogleSuccess = async (credentialResponse: { credential?: string }) => {
    const idToken = credentialResponse.credential
    if (!idToken) return
    try {
      const { access_token } = await authApi.google(idToken)
      login(access_token)
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
    <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--color-bg)] px-4">
      <div className="w-full max-w-md text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-[var(--color-text)] mb-2">
          Secured String Matching
        </h1>
        <p className="text-[var(--color-muted)] mb-8">
          Search on encrypted data without revealing it.
        </p>
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-8 shadow-xl">
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
        </div>
      </div>
    </div>
  )
}

export default function Login() {
  return <LoginContent />
}
