import { useState, useCallback } from 'react'
import { documentsApi } from '../api/client'

export default function LocateDecryptTools() {
  const [docIds, setDocIds] = useState<string[]>([])
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [locateOpen, setLocateOpen] = useState(false)
  const [decryptOpen, setDecryptOpen] = useState(false)
  const [selectedDocId, setSelectedDocId] = useState('')
  const [pathInfo, setPathInfo] = useState<{ encrypted_path: string; original_filename: string } | null>(null)
  const [pathError, setPathError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const loadDocs = useCallback(async (): Promise<string[]> => {
    setLoadingDocs(true)
    try {
      const { document_ids } = await documentsApi.list({ limit: 500 })
      setDocIds(document_ids)
      return document_ids
    } catch {
      setDocIds([])
      return []
    } finally {
      setLoadingDocs(false)
    }
  }, [])

  const onSelectDoc = useCallback(async (docId: string) => {
    setSelectedDocId(docId)
    setPathInfo(null)
    setPathError(null)
    if (!docId) return
    try {
      const res = await documentsApi.getEncryptedPath(docId)
      setPathInfo({ encrypted_path: res.encrypted_path, original_filename: res.original_filename })
    } catch (e) {
      setPathError(e instanceof Error ? e.message : 'Failed to load path')
    }
  }, [])

  const openLocate = () => {
    setPathInfo(null)
    setPathError(null)
    setLocateOpen(true)
    loadDocs().then(ids => {
      if (ids.length) {
        setSelectedDocId(ids[0])
        onSelectDoc(ids[0])
      }
    })
  }

  const openDecrypt = () => {
    setPathInfo(null)
    setPathError(null)
    setDecryptOpen(true)
    loadDocs().then(ids => {
      if (ids.length) {
        setSelectedDocId(ids[0])
        onSelectDoc(ids[0])
      }
    })
  }

  const copyPath = () => {
    if (pathInfo?.encrypted_path) {
      navigator.clipboard.writeText(pathInfo.encrypted_path)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <>
      <div className="flex flex-wrap gap-4 mt-8 p-4 rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)]/30">
        <button
          type="button"
          onClick={openLocate}
          className="flex flex-col items-center justify-center min-w-[180px] py-4 px-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] hover:bg-[var(--color-surface)] transition text-left"
        >
          <span className="text-sm font-mono text-[var(--color-muted)] mb-2">abc → 101010</span>
          <span className="text-sm font-medium text-[var(--color-text)]">Locate Encrypted File</span>
        </button>
        <button
          type="button"
          onClick={openDecrypt}
          className="flex flex-col items-center justify-center min-w-[180px] py-4 px-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] hover:bg-[var(--color-surface)] transition text-left"
        >
          <span className="text-sm font-mono text-[var(--color-muted)] mb-2">101010 → abc</span>
          <span className="text-sm font-medium text-[var(--color-text)]">Decrypt File Name</span>
        </button>
      </div>

      {/* Locate Encrypted File modal */}
      {locateOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50" onClick={() => setLocateOpen(false)}>
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl max-w-lg w-full p-6 shadow-xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-medium text-[var(--color-text)] mb-2">Select file inside vault</h3>
            <p className="text-sm text-[var(--color-muted)] mb-4">Choose a document to see its encrypted storage path.</p>
            {loadingDocs ? (
              <p className="text-sm text-[var(--color-muted)]">Loading…</p>
            ) : docIds.length === 0 ? (
              <p className="text-sm text-[var(--color-muted)]">No documents in vault. Upload a file first.</p>
            ) : (
              <>
                <label className="block text-sm font-medium text-[var(--color-text)] mb-2">File name:</label>
                <select
                  value={selectedDocId}
                  onChange={e => onSelectDoc(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] mb-4"
                >
                  {docIds.map(id => (
                    <option key={id} value={id}>{id}</option>
                  ))}
                </select>
                {pathError && <p className="text-red-400 text-sm mb-2">{pathError}</p>}
                {pathInfo && (
                  <div className="space-y-2 mb-4">
                    <label className="block text-xs font-medium text-[var(--color-muted)]">Encrypted path:</label>
                    <div className="flex gap-2">
                      <code className="flex-1 px-3 py-2 rounded bg-[var(--color-bg)] text-sm text-[var(--color-text)] break-all">
                        {pathInfo.encrypted_path}
                      </code>
                      <button
                        type="button"
                        onClick={copyPath}
                        className="shrink-0 px-3 py-2 rounded-lg bg-[var(--color-primary)] text-white text-sm font-medium"
                      >
                        {copied ? 'Copied' : 'Copy'}
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
            <div className="flex justify-end gap-2 mt-4">
              <button type="button" onClick={() => setLocateOpen(false)} className="px-4 py-2 rounded-lg border border-[var(--color-border)] text-[var(--color-text)]">
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Decrypt File Name modal */}
      {decryptOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50" onClick={() => setDecryptOpen(false)}>
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl max-w-lg w-full p-6 shadow-xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-medium text-[var(--color-text)] mb-2">Decrypt file name</h3>
            <p className="text-sm text-[var(--color-muted)] mb-4">Select a document to see encrypted ID → original filename.</p>
            {loadingDocs ? (
              <p className="text-sm text-[var(--color-muted)]">Loading…</p>
            ) : docIds.length === 0 ? (
              <p className="text-sm text-[var(--color-muted)]">No documents in vault.</p>
            ) : (
              <>
                <label className="block text-sm font-medium text-[var(--color-text)] mb-2">Encrypted document ID:</label>
                <select
                  value={selectedDocId}
                  onChange={e => onSelectDoc(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] mb-4"
                >
                  {docIds.map(id => (
                    <option key={id} value={id}>{id}</option>
                  ))}
                </select>
                {pathError && <p className="text-red-400 text-sm mb-2">{pathError}</p>}
                {pathInfo && (
                  <div className="space-y-2 mb-4">
                    <div className="flex items-center gap-2 text-sm">
                      <code className="px-2 py-1 rounded bg-[var(--color-bg)] text-[var(--color-muted)]">{selectedDocId}</code>
                      <span className="text-[var(--color-muted)]">→</span>
                      <span className="text-[var(--color-text)] font-medium">{pathInfo.original_filename}</span>
                    </div>
                  </div>
                )}
              </>
            )}
            <div className="flex justify-end gap-2 mt-4">
              <button type="button" onClick={() => setDecryptOpen(false)} className="px-4 py-2 rounded-lg border border-[var(--color-border)] text-[var(--color-text)]">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
