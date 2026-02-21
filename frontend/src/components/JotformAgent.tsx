import { useEffect } from 'react'

const JOTFORM_AGENT_SCRIPT =
  'https://cdn.jotfor.ms/agent/embedjs/019c81f82a1277a5baac5e455441099de359/embed.js'

/**
 * Loads the Jotform AI agent script only when this component mounts.
 * Used so the assistant appears only after the user has signed in (this component
 * is rendered only inside protected routes).
 */
export default function JotformAgent() {
  useEffect(() => {
    if (document.querySelector(`script[src="${JOTFORM_AGENT_SCRIPT}"]`)) return
    const script = document.createElement('script')
    script.src = JOTFORM_AGENT_SCRIPT
    script.defer = true
    document.body.appendChild(script)
    return () => {
      script.remove()
    }
  }, [])
  return null
}
