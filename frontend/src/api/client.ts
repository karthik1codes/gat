// Use explicit env or default to backend on same host in dev (so it works without restart after .env change)
function getApiBase(): string {
  const env = import.meta.env.VITE_API_URL
  if (env) return env
  if (typeof window !== 'undefined' && /^localhost$|^127\.0\.0\.1$/i.test(window.location.hostname))
    return 'http://localhost:8000'
  return ''
}
export const API_BASE = getApiBase()

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

/** Server may return encrypted filename payload (decrypt client-side with vault key). */
export interface EncryptedFilenamePayload {
  encrypted_filename: string
  filename_iv: string
  filename_tag: string
}

/** Upload debug metadata (Judge Mode). Safe fields only — no keys or plaintext. */
export interface UploadDebugFile {
  encrypted_filename: string
  keyword_count: number
  generated_tokens: string[]
  encryption_algorithm: string
  iv_length: number
  ciphertext_size: number
}

export interface UploadResponse {
  uploaded: { id: string; filename: string; encrypted_path: string }[]
  count: number
  debug?: { files: UploadDebugFile[] }
}

/** Search debug metadata (Judge Mode). Safe fields only. */
export interface SearchDebugInfo {
  search_token: string
  matched_encrypted_doc_ids: string[]
  encryption_algorithm: string
  token_algorithm: string
  index_lookup_performed: boolean
  result_count: number
}

export interface SearchResponse {
  query: string
  document_ids: string[]
  total?: number
  debug?: SearchDebugInfo
}

export interface SecurityInfo {
  encryption: string
  token_generation: string
  key_size_bits: number
  leakage_profile: { search_pattern: boolean; access_pattern: boolean; content_leakage: boolean }
}

export const documentsApi = {
  upload: (files: File[], debug?: boolean) => {
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    const path = debug ? '/api/documents/upload?debug=true' : '/api/documents/upload'
    return api<UploadResponse>(path, { method: 'POST', body: form })
  },
  search: (q: string, opts?: { padTo?: number; searchType?: string; topK?: number; keywords?: string; mode?: 'and' | 'or'; skip?: number; limit?: number; debug?: boolean }) => {
    const params = new URLSearchParams({ q })
    if (opts?.padTo != null && opts.padTo > 0) params.set('pad_to', String(opts.padTo))
    if (opts?.searchType) params.set('search_type', opts.searchType)
    if (opts?.topK != null && opts.topK > 0) params.set('top_k', String(opts.topK))
    if (opts?.keywords) params.set('keywords', opts.keywords)
    if (opts?.mode) params.set('mode', opts.mode)
    if (opts?.skip != null) params.set('skip', String(opts.skip))
    if (opts?.limit != null) params.set('limit', String(opts.limit))
    if (opts?.debug) params.set('debug', 'true')
    return api<SearchResponse>(`/api/documents/search?${params}`)
  },
  list: (opts?: { skip?: number; limit?: number }) => {
    const params = new URLSearchParams()
    if (opts?.skip != null) params.set('skip', String(opts.skip))
    if (opts?.limit != null) params.set('limit', String(opts.limit ?? 100))
    const qs = params.toString()
    return api<{
      document_ids: string[]
      total: number
      documents?: { id: string; original_filename?: string; encrypted_filename_payload?: EncryptedFilenamePayload }[]
    }>(`/api/documents/${qs ? `?${qs}` : ''}`)
  },
  delete: (docId: string) =>
    api<{ deleted: string }>(`/api/documents/${encodeURIComponent(docId)}`, { method: 'DELETE' }),
  getContent: (docId: string) => apiText(`/api/documents/${encodeURIComponent(docId)}/content`),
  getEncryptedPath: (docId: string) =>
    api<
      | { doc_id: string; encrypted_path: string; original_filename: string }
      | { doc_id: string; encrypted_path: string; encrypted_filename_payload: EncryptedFilenamePayload }
    >(`/api/documents/${encodeURIComponent(docId)}/encrypted-path`),
}

export const securityInfoApi = {
  get: () => api<SecurityInfo>('/api/security-info'),
}

/** Single benchmark run: N docs. */
export interface BenchmarkRun {
  num_docs: number
  doc_size_bytes: number
  use_sqlite: boolean
  encryption_sec?: number
  encryption_time_ms?: number
  upload_total_sec?: number
  search_latency_sec?: number
  search_time_ms?: number
  index_size_bytes?: number
  index_size_kb?: number
  token_gen_100_sec?: number
  error?: string
}

/** Scaling analysis derived from benchmark runs. */
export interface ScalingAnalysis {
  summary: string
  encryption_time_per_doc_ms: number | null
  search_time_ms_at_max_n: number | null
  index_bytes_per_doc: number | null
  max_n_tested?: number
}

export interface BenchmarkResponse {
  benchmark_results: BenchmarkRun[]
  dataset_sizes: number[]
  doc_size_bytes: number
  scaling_analysis: ScalingAnalysis
  metrics_summary?: Record<string, string>
}

export const benchmarkApi = {
  run: () => api<BenchmarkResponse>('/api/benchmark/run', { method: 'POST' }),
}

export type VaultStatus = { state: 'LOCKED' | 'UNLOCKED'; initialized: boolean }
export type VaultStats = {
  total_encrypted_files: number
  total_encrypted_size_bytes: number
  index_size_bytes: number
  encryption_algorithm: string
  kdf_algorithm: string
  kdf_iterations_equivalent: number
  last_unlock_timestamp: number | null
  vault_state: string
}

export const vaultApi = {
  status: () => api<VaultStatus>('/api/vault/status'),
  unlock: (password: string) =>
    api<{ state: string }>('/api/vault/unlock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    }),
  lock: () =>
    api<{ state: string }>('/api/vault/lock', { method: 'POST' }),
  stats: () => api<VaultStats>('/api/vault/stats'),
  /** Key for client-side string encrypt/decrypt (Locate/Decrypt tools). Vault must be unlocked. */
  getClientStringKey: () =>
    api<{ key_base64: string }>('/api/vault/client-string-key'),
}
