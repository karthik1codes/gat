const API_BASE = import.meta.env.VITE_API_URL || ''

function getToken(): string | null {
  return localStorage.getItem('access_token')
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken()
  const headers: HeadersInit = {
    ...(options.headers as Record<string, string>),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export async function apiText(path: string): Promise<string> {
  const token = getToken()
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error(await res.text() || res.statusText)
  return res.text()
}

export const authApi = {
  google: (id_token: string) =>
    api<{ access_token: string; user: { id: string; email: string; name: string | null; picture: string | null } }>(
      '/api/auth/google',
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id_token }) }
    ),
  me: () =>
    api<{ id: string; email: string; name: string | null; picture: string | null }>('/api/auth/me'),
}

export const documentsApi = {
  upload: (files: File[]) => {
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    return api<{ uploaded: { id: string; filename: string }[]; count: number }>('/api/documents/upload', {
      method: 'POST',
      body: form,
    })
  },
  search: (q: string) =>
    api<{ query: string; document_ids: string[] }>(`/api/documents/search?q=${encodeURIComponent(q)}`),
  list: () => api<{ document_ids: string[] }>('/api/documents/'),
  getContent: (docId: string) => apiText(`/api/documents/${encodeURIComponent(docId)}/content`),
}
