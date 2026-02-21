import { useState, useCallback, useEffect } from 'react'
import { documentsApi } from '../api/client'

export default function Dashboard() {
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState<string[] | null>(null)
  const [searching, setSearching] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [docIds, setDocIds] = useState<string[]>([])
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [viewDocId, setViewDocId] = useState<string | null>(null)
  const [viewContent, setViewContent] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadDocList = useCallback(async () => {
    setLoadingDocs(true)
    setError(null)
    try {
      const { document_ids } = await documentsApi.list()
      setDocIds(document_ids)
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
      const res = await documentsApi.search(query.trim())
      setSearchResults(res.document_ids)
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
    try {
      await documentsApi.upload(Array.from(files))
      await loadDocList()
      e.target.value = ''
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
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
      </section>

      {/* Search */}
      <section className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-6">
        <h2 className="text-lg font-medium text-[var(--color-text)] mb-3">Search encrypted data</h2>
        <p className="text-[var(--color-muted)] text-sm mb-4">
          Enter a keyword. Matching is done on the server using a search token — the server never sees your query.
        </p>
        <form onSubmit={handleSearch} className="flex gap-2 flex-wrap">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. invoice, confidential"
            className="flex-1 min-w-[200px] px-4 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] placeholder-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          />
          <button
            type="submit"
            disabled={searching}
            className="px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium hover:bg-[var(--color-primary-hover)] transition disabled:opacity-50"
          >
            {searching ? 'Searching…' : 'Search'}
          </button>
        </form>
        {searchResults !== null && (
          <div className="mt-4">
            <p className="text-sm text-[var(--color-muted)] mb-2">
              Found {searchResults.length} document(s)
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
          <ul className="space-y-1">
            {docIds.map((id) => (
              <li key={id}>
                <button
                  type="button"
                  onClick={() => openDocument(id)}
                  className="text-[var(--color-accent)] hover:underline text-left"
                >
                  {id}
                </button>
              </li>
            ))}
          </ul>
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
