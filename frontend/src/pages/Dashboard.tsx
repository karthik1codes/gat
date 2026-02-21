import { useState, useCallback, useEffect } from 'react'
import { documentsApi } from '../api/client'
import { useVault } from '../hooks/useVault'

export default function Dashboard() {
  const { refresh: refreshVault } = useVault()
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState<string[] | null>(null)
  const [searching, setSearching] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [docIds, setDocIds] = useState<string[]>([])
  const [totalDocs, setTotalDocs] = useState(0)
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [listSkip, setListSkip] = useState(0)
  const listLimit = 50
  const [viewDocId, setViewDocId] = useState<string | null>(null)
  const [viewContent, setViewContent] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [padSearch, setPadSearch] = useState(false)
  const [searchType, setSearchType] = useState<'keyword' | 'substring' | 'fuzzy' | 'ranked'>('keyword')
  const [topK, setTopK] = useState(20)
  const [searchTotal, setSearchTotal] = useState<number | null>(null)
  const [lastUploaded, setLastUploaded] = useState<{ id: string; filename: string; encrypted_path: string }[]>([])
  const [copiedPath, setCopiedPath] = useState<string | null>(null)

  const loadDocList = useCallback(async () => {
    setLoadingDocs(true)
    setError(null)
    try {
      const { document_ids, total } = await documentsApi.list({ skip: 0, limit: listLimit })
      setDocIds(document_ids)
      setTotalDocs(total)
      setListSkip(0)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load documents')
    } finally {
      setLoadingDocs(false)
    }
  }, [])

  useEffect(() => { loadDocList() }, [loadDocList])

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    setSearching(true)
    setError(null)
    setSearchResults(null)
    try {
      const res = await documentsApi.search(query.trim(), {
        padTo: padSearch ? 50 : undefined,
        searchType,
        topK: searchType === 'ranked' ? topK : undefined,
      })
      setSearchResults(res.document_ids)
      setSearchTotal(res.total ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed')
    } finally {
      setSearching(false)
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files?.length) return
    setUploading(true)
    setError(null)
    setLastUploaded([])
    try {
      const res = await documentsApi.upload(Array.from(files))
      setLastUploaded(res.uploaded.map((u) => ({ id: u.id, filename: u.filename, encrypted_path: u.encrypted_path })))
      await loadDocList()
      refreshVault()
      e.target.value = ''
      // Scroll to encrypted path section so user sees where files were stored
      document.getElementById('locate-decrypt-tools')?.scrollIntoView({ behavior: 'smooth' })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const copyEncryptedPath = (path: string) => {
    navigator.clipboard.writeText(path)
    setCopiedPath(path)
    setTimeout(() => setCopiedPath(null), 2000)
  }

  const handleDelete = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Delete this document? This cannot be undone.')) return
    setError(null)
    try {
      await documentsApi.delete(docId)
      await loadDocList()
      refreshVault()
      if (viewDocId === docId) setViewDocId(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    }
  }

  const loadMoreDocs = async () => {
    setLoadingDocs(true)
    setError(null)
    try {
      const nextSkip = listSkip + listLimit
      const { document_ids, total } = await documentsApi.list({ skip: nextSkip, limit: listLimit })
      setDocIds((prev) => [...prev, ...document_ids])
      setTotalDocs(total)
      setListSkip(nextSkip)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load more')
    } finally {
      setLoadingDocs(false)
    }
  }

  const openDocument = async (docId: string) => {
    setViewDocId(docId)
    setViewContent(null)
    try {
      const text = await documentsApi.getContent(docId)
      setViewContent(text)
    } catch (e) {
      setViewContent('(Could not load content)')
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-[var(--color-text)] mb-1">Dashboard</h1>
        <p className="text-[var(--color-muted)] text-sm">
          Upload documents (encrypted). Search by keyword. Only you can decrypt.
        </p>
        <p className="text-[var(--color-muted)] text-xs mt-2">
          How search works: your documents and keywords are encrypted. The server only sees opaque tokens and returns document IDs; it never sees your query text or file contents.{' '}
          <a
            href={`${import.meta.env.VITE_API_URL || ''}/api/docs/threat-model`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[var(--color-accent)] hover:underline"
          >
            Privacy & threat model
          </a>
        </p>
      </div>

      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 text-red-200 text-sm p-4">
          {error}
        </div>
      )}

      {/* Upload */}
      <section className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-6">
        <h2 className="text-lg font-medium text-[var(--color-text)] mb-3">Upload documents</h2>
        <p className="text-[var(--color-muted)] text-sm mb-4">
          Files are encrypted and indexed by keywords. Server never sees plaintext.
        </p>
        <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium cursor-pointer hover:bg-[var(--color-primary-hover)] transition disabled:opacity-50">
          <input
            type="file"
            multiple
            accept=".txt,.md,.csv"
            className="sr-only"
            onChange={handleUpload}
            disabled={uploading}
          />
          {uploading ? 'Uploading…' : 'Choose files'}
        </label>
        {lastUploaded.length > 0 && (
          <div className="mt-4 p-4 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)]">
            <p className="text-sm font-medium text-[var(--color-text)] mb-2">Uploaded and encrypted — stored at:</p>
            <ul className="space-y-2">
              {lastUploaded.map((u) => (
                <li key={u.id} className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-[var(--color-muted)] truncate max-w-[140px]" title={u.filename}>{u.filename}</span>
                  <code className="flex-1 min-w-0 truncate px-2 py-1 rounded bg-[var(--color-surface)] text-[var(--color-text)]" title={u.encrypted_path}>
                    {u.encrypted_path}
                  </code>
                  <button
                    type="button"
                    onClick={() => copyEncryptedPath(u.encrypted_path)}
                    className="shrink-0 px-2 py-1 rounded bg-[var(--color-primary)] text-white text-xs font-medium"
                  >
                    {copiedPath === u.encrypted_path ? 'Copied' : 'Copy path'}
                  </button>
                </li>
              ))}
            </ul>
            <p className="text-xs text-[var(--color-muted)] mt-2">Use &quot;Locate Encrypted File&quot; below to open this path for any document.</p>
          </div>
        )}
      </section>

      {/* Search */}
      <section className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-6">
        <h2 className="text-lg font-medium text-[var(--color-text)] mb-3">Search encrypted data</h2>
        <p className="text-[var(--color-muted)] text-sm mb-4">
          Enter a keyword. Matching is done on the server using a search token — the server never sees your query.
        </p>
        <p className="text-[var(--color-muted)] text-xs mb-3">
          Privacy: you can pad the result count so the server cannot see the exact number of matches.
        </p>
        <form onSubmit={handleSearch} className="flex flex-col gap-3">
          <div className="flex gap-2 flex-wrap items-center">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. invoice, confidential"
            className="flex-1 min-w-[200px] px-4 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] placeholder-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          />
          <select
            value={searchType}
            onChange={(e) => setSearchType(e.target.value as 'keyword' | 'substring' | 'fuzzy' | 'ranked')}
            className="px-3 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
            title="Keyword: exact word. Substring: contains phrase. Fuzzy: similar spelling. Ranked: by relevance (TF-IDF)."
          >
            <option value="keyword">Keyword</option>
            <option value="substring">Substring</option>
            <option value="fuzzy">Fuzzy</option>
            <option value="ranked">Ranked</option>
          </select>
          {searchType === 'ranked' && (
            <label className="flex items-center gap-2 text-sm text-[var(--color-muted)]">
              Top
              <input
                type="number"
                min={1}
                max={100}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value) || 20)}
                className="w-14 px-2 py-1 rounded bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)]"
              />
            </label>
          )}
          <button
            type="submit"
            disabled={searching}
            className="px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium hover:bg-[var(--color-primary-hover)] transition disabled:opacity-50"
          >
            {searching ? 'Searching…' : 'Search'}
          </button>
          </div>
          <label className="flex items-center gap-2 text-sm text-[var(--color-muted)] cursor-pointer">
            <input
              type="checkbox"
              checked={padSearch}
              onChange={(e) => setPadSearch(e.target.checked)}
              className="rounded border-[var(--color-border)]"
            />
            Pad result count for privacy (hides exact match count from server)
          </label>
        </form>
        {searchResults !== null && (
          <div className="mt-4">
            <p className="text-sm text-[var(--color-muted)] mb-2">
              Found {searchResults.length} document(s)
              {searchTotal != null && searchTotal !== searchResults.length ? ` (total: ${searchTotal})` : ''}
            </p>
            <ul className="space-y-1">
              {searchResults.length === 0 ? (
                <li className="text-[var(--color-muted)] text-sm">No matches.</li>
              ) : (
                searchResults.map((id) => (
                  <li key={id}>
                    <button
                      type="button"
                      onClick={() => openDocument(id)}
                      className="text-[var(--color-accent)] hover:underline text-left"
                    >
                      {id}
                    </button>
                  </li>
                ))
              )}
            </ul>
          </div>
        )}
      </section>

      {/* Document list */}
      <section className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-medium text-[var(--color-text)]">Your documents</h2>
          <button
            type="button"
            onClick={loadDocList}
            disabled={loadingDocs}
            className="text-sm text-[var(--color-primary)] hover:underline disabled:opacity-50"
          >
            {loadingDocs ? 'Loading…' : 'Refresh'}
          </button>
        </div>
        {docIds.length === 0 && !loadingDocs ? (
          <p className="text-[var(--color-muted)] text-sm">No documents yet. Upload some above.</p>
        ) : (
          <>
            <ul className="space-y-1">
              {docIds.map((id) => (
                <li key={id} className="flex items-center justify-between gap-2 group">
                  <button
                    type="button"
                    onClick={() => openDocument(id)}
                    className="text-[var(--color-accent)] hover:underline text-left flex-1 truncate"
                  >
                    {id}
                  </button>
                  <button
                    type="button"
                    onClick={(e) => handleDelete(id, e)}
                    className="text-red-400 hover:text-red-300 text-sm opacity-70 group-hover:opacity-100"
                    title="Delete document"
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
            {totalDocs > docIds.length && (
              <button
                type="button"
                onClick={loadMoreDocs}
                disabled={loadingDocs}
                className="mt-3 text-sm text-[var(--color-primary)] hover:underline disabled:opacity-50"
              >
                {loadingDocs ? 'Loading…' : `Load more (${docIds.length} of ${totalDocs})`}
              </button>
            )}
          </>
        )}
      </section>

      {/* View document modal */}
      {viewDocId && (
        <div
          className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50"
          onClick={() => setViewDocId(null)}
        >
          <div
            className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b border-[var(--color-border)]">
              <span className="font-medium text-[var(--color-text)] truncate">{viewDocId}</span>
              <button
                type="button"
                onClick={() => setViewDocId(null)}
                className="text-[var(--color-muted)] hover:text-[var(--color-text)]"
              >
                Close
              </button>
            </div>
            <pre className="p-4 overflow-auto text-sm text-[var(--color-text)] whitespace-pre-wrap flex-1">
              {viewContent ?? 'Loading…'}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
