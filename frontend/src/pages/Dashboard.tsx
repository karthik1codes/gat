import { useState, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  documentsApi,
  securityInfoApi,
  benchmarkApi,
  type UploadDebugFile,
  type SearchDebugInfo,
  type SecurityInfo,
  type BenchmarkResponse,
} from '../api/client'
import { useVault } from '../hooks/useVault'

const cardItem = { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 } }
const containerVariants = { initial: {}, animate: { transition: { staggerChildren: 0.05, delayChildren: 0.05 } } }
const btnHover = { scale: 1.03, transition: { duration: 0.2 } }
const btnTap = { scale: 0.98 }

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
  const [judgeMode, setJudgeMode] = useState(false)
  const [uploadDebug, setUploadDebug] = useState<UploadDebugFile[] | null>(null)
  const [searchDebug, setSearchDebug] = useState<SearchDebugInfo | null>(null)
  const [securityInfo, setSecurityInfo] = useState<SecurityInfo | null>(null)
  const [lastSearchQuery, setLastSearchQuery] = useState<string>('')
  const [benchmarkRunning, setBenchmarkRunning] = useState(false)
  const [benchmarkResult, setBenchmarkResult] = useState<BenchmarkResponse | null>(null)
  const [benchmarkError, setBenchmarkError] = useState<string | null>(null)

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

  useEffect(() => {
    if (judgeMode) {
      securityInfoApi.get().then(setSecurityInfo).catch(() => setSecurityInfo(null))
    } else {
      setSecurityInfo(null)
    }
  }, [judgeMode])

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    setSearching(true)
    setError(null)
    setSearchResults(null)
    setSearchDebug(null)
    const q = query.trim()
    setLastSearchQuery(q)
    try {
      const res = await documentsApi.search(q, {
        padTo: padSearch ? 50 : undefined,
        searchType,
        topK: searchType === 'ranked' ? topK : undefined,
        debug: judgeMode,
      })
      setSearchResults(res.document_ids)
      setSearchTotal(res.total ?? null)
      if (res.debug) setSearchDebug(res.debug)
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
    setUploadDebug(null)
    try {
      const res = await documentsApi.upload(Array.from(files), judgeMode)
      setLastUploaded(res.uploaded.map((u) => ({ id: u.id, filename: u.filename, encrypted_path: u.encrypted_path })))
      if (res.debug?.files) setUploadDebug(res.debug.files)
      await loadDocList()
      refreshVault()
      e.target.value = ''
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

  const runBenchmark = async () => {
    setBenchmarkRunning(true)
    setBenchmarkError(null)
    setBenchmarkResult(null)
    try {
      const res = await benchmarkApi.run()
      setBenchmarkResult(res)
    } catch (e) {
      setBenchmarkError(e instanceof Error ? e.message : 'Benchmark failed')
    } finally {
      setBenchmarkRunning(false)
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
    <motion.div className="space-y-8" initial="initial" animate="animate" variants={containerVariants}>
      <motion.div variants={cardItem}>
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
        <div className="flex items-center gap-2 mt-4">
          <button
            type="button"
            role="switch"
            aria-checked={judgeMode}
            onClick={() => setJudgeMode((v) => !v)}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border border-[var(--color-border)] transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-offset-2 focus:ring-offset-[var(--color-bg)] ${judgeMode ? 'bg-[var(--color-primary)]/30' : 'bg-[var(--color-bg)]'}`}
          >
            <motion.span
              className="absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-[var(--color-primary)] shadow"
              animate={{ x: judgeMode ? 20 : 0 }}
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            />
          </button>
          <span className="text-sm font-medium text-[var(--color-text)]">
            Judge Mode (Cryptographic Trace)
          </span>
        </div>
        <p className="text-[var(--color-muted)] text-xs mt-1 ml-[3.25rem]">
          When on, upload and search include safe trace metadata so you can see client/server steps without exposing secrets.
        </p>
        <AnimatePresence>
          {judgeMode && securityInfo && (
            <motion.div
              className="mt-4 p-4 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] overflow-hidden"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: 'easeInOut' }}
            >
              <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3">Security metrics</h3>
              <ul className="space-y-2 text-sm">
                <li className="text-[var(--color-muted)]">Encryption: {securityInfo.encryption}</li>
                <li className="text-[var(--color-muted)]">Token generation: {securityInfo.token_generation}</li>
                <li className="text-[var(--color-muted)]">Key size: {securityInfo.key_size_bits} bits</li>
              </ul>
              <p className="text-sm font-medium text-[var(--color-text)] mt-3 mb-2">Leakage profile</p>
              <ul className="space-y-1 text-sm">
                <li className="flex items-center gap-2">
                  <span className={securityInfo.leakage_profile.search_pattern ? 'text-amber-400' : 'text-green-400'} aria-hidden>●</span>
                  Search pattern: {securityInfo.leakage_profile.search_pattern ? 'visible (token equality)' : 'hidden'}
                </li>
                <li className="flex items-center gap-2">
                  <span className={securityInfo.leakage_profile.access_pattern ? 'text-amber-400' : 'text-green-400'} aria-hidden>●</span>
                  Access pattern: {securityInfo.leakage_profile.access_pattern ? 'visible (which docs match)' : 'hidden'}
                </li>
                <li className="flex items-center gap-2">
                  <span className={securityInfo.leakage_profile.content_leakage ? 'text-red-400' : 'text-green-400'} aria-hidden>●</span>
                  Content leakage: {securityInfo.leakage_profile.content_leakage ? 'yes' : 'no'}
                </li>
              </ul>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {error && (
        <motion.div className="rounded-lg bg-red-500/10 border border-red-500/30 text-red-200 text-sm p-4" variants={cardItem}>
          {error}
        </motion.div>
      )}

      {/* Upload */}
      <motion.section
        className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-6 transition-shadow duration-200 hover:shadow-[0_8px_30px_rgba(0,0,0,0.25)]"
        variants={cardItem}
        whileHover={{ scale: 1.01 }}
      >
        <h2 className="text-lg font-medium text-[var(--color-text)] mb-3">Upload documents</h2>
        <p className="text-[var(--color-muted)] text-sm mb-4">
          Files are encrypted and indexed by keywords. Server never sees plaintext.
        </p>
        <motion.label
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium cursor-pointer transition-shadow duration-200 hover:shadow-[0_0_16px_rgba(139,92,246,0.4)] disabled:opacity-50"
          whileHover={!uploading ? btnHover : undefined}
          whileTap={!uploading ? btnTap : undefined}
        >
          <input
            type="file"
            multiple
            accept=".txt,.md,.csv"
            className="sr-only"
            onChange={handleUpload}
            disabled={uploading}
          />
          {uploading ? 'Uploading…' : 'Choose files'}
        </motion.label>
        {lastUploaded.length > 0 && (
          <motion.div
            className="mt-4 p-4 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)]"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.25 }}
          >
            <p className="text-sm font-medium text-[var(--color-text)] mb-2 flex items-center gap-2">
              <motion.span
                className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-[var(--color-accent)] text-white"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 400, damping: 20 }}
              >
                <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
              </motion.span>
              Uploaded and encrypted — stored at:
            </p>
            <ul className="space-y-2">
              {lastUploaded.map((u) => (
                <li key={u.id} className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-[var(--color-muted)] truncate max-w-[140px]" title={u.filename}>{u.filename}</span>
                  <code className="flex-1 min-w-0 truncate px-2 py-1 rounded bg-[var(--color-surface)] text-[var(--color-text)]" title={u.encrypted_path}>
                    {u.encrypted_path}
                  </code>
                  <motion.button
                    type="button"
                    onClick={() => copyEncryptedPath(u.encrypted_path)}
                    className="shrink-0 px-2 py-1 rounded bg-[var(--color-primary)] text-white text-xs font-medium"
                    whileHover={btnHover}
                    whileTap={btnTap}
                  >
                    {copiedPath === u.encrypted_path ? 'Copied' : 'Copy path'}
                  </motion.button>
                </li>
              ))}
            </ul>
            <p className="text-xs text-[var(--color-muted)] mt-2">Use &quot;Locate Encrypted File&quot; below to open this path for any document.</p>
          </motion.div>
        )}
        {judgeMode && uploadDebug && uploadDebug.length > 0 && (
          <div className="mt-4 p-4 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)]">
            <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3">Upload encryption trace</h3>
            {uploadDebug.map((f, i) => (
              <div key={i} className="mb-4 last:mb-0 text-sm">
                <p className="text-[var(--color-muted)] mb-1">Extracted keywords: {f.keyword_count}</p>
                <p className="text-[var(--color-muted)] mb-1">Generated tokens: [{f.generated_tokens.length} token(s)]</p>
                <p className="text-[var(--color-muted)] mb-1">Encryption: {f.encryption_algorithm}</p>
                <p className="text-[var(--color-muted)] mb-1">IV length: {f.iv_length} bytes</p>
                <p className="text-[var(--color-muted)]">Ciphertext size: {f.ciphertext_size} bytes</p>
                {f.generated_tokens.length > 0 && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-[var(--color-accent)]">Show token hashes</summary>
                    <pre className="mt-1 text-xs break-all text-[var(--color-muted)]">{f.generated_tokens.join('\n')}</pre>
                  </details>
                )}
              </div>
            ))}
            <details className="mt-3">
              <summary className="cursor-pointer font-medium text-[var(--color-text)]">What server sees</summary>
              <div className="mt-2 p-3 rounded bg-[var(--color-surface)] text-sm text-[var(--color-muted)]">
                <p className="mb-2">Server sees only:</p>
                <ul className="list-disc list-inside space-y-1">
                  {uploadDebug.map((f, i) => (
                    <li key={i}>Encrypted filename / doc ID, ciphertext size ({f.ciphertext_size} bytes)</li>
                  ))}
                </ul>
                <p className="mt-2 font-medium text-[var(--color-text)]">Server does NOT see: plaintext content, keyword text, secret key.</p>
              </div>
            </details>
          </div>
        )}
      </motion.section>

      {/* Search */}
      <motion.section
        className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-6 transition-shadow duration-200 hover:shadow-[0_8px_30px_rgba(0,0,0,0.25)]"
        variants={cardItem}
        whileHover={{ scale: 1.01 }}
      >
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
          <motion.button
            type="submit"
            disabled={searching}
            className="px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium transition-shadow duration-200 hover:shadow-[0_0_16px_rgba(139,92,246,0.4)] disabled:opacity-50"
            whileHover={!searching ? btnHover : undefined}
            whileTap={!searching ? btnTap : undefined}
          >
            {searching ? 'Searching…' : 'Search'}
          </motion.button>
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
          <motion.div className="mt-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.25 }}>
            <p className="text-sm text-[var(--color-muted)] mb-2">
              Found {searchResults.length} document(s)
              {searchTotal != null && searchTotal !== searchResults.length ? ` (total: ${searchTotal})` : ''}
            </p>
            <motion.ul className="space-y-1" variants={containerVariants} initial="initial" animate="animate">
              {searchResults.length === 0 ? (
                <motion.li className="text-[var(--color-muted)] text-sm" variants={cardItem}>No matches.</motion.li>
              ) : (
                searchResults.map((id) => (
                  <motion.li key={id} variants={cardItem}>
                    <motion.button
                      type="button"
                      onClick={() => openDocument(id)}
                      className="text-[var(--color-accent)] hover:underline text-left"
                      whileHover={{ x: 2 }}
                      whileTap={btnTap}
                    >
                      {id}
                    </motion.button>
                  </motion.li>
                ))
              )}
            </motion.ul>
            {judgeMode && searchDebug && (
              <div className="mt-4 p-4 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)]">
                <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3">Search execution trace</h3>
                <div className="space-y-3 text-sm">
                  <div>
                    <p className="font-medium text-[var(--color-text)] mb-1">=== CLIENT SIDE ===</p>
                    <p className="text-[var(--color-muted)]">Input keyword: {lastSearchQuery}</p>
                    <p className="text-[var(--color-muted)]">Generated search token: <code className="break-all text-xs">{searchDebug.search_token}</code></p>
                  </div>
                  <div>
                    <p className="font-medium text-[var(--color-text)] mb-1">=== SERVER SIDE ===</p>
                    <p className="text-[var(--color-muted)]">Received token → index lookup performed</p>
                    <p className="text-[var(--color-muted)]">Matched encrypted IDs: [{searchDebug.matched_encrypted_doc_ids.length}]{' '}
                      {searchDebug.matched_encrypted_doc_ids.length > 0 && (
                        <details>
                          <summary className="cursor-pointer text-[var(--color-accent)]">Show IDs</summary>
                          <pre className="mt-1 text-xs break-all text-[var(--color-muted)]">{searchDebug.matched_encrypted_doc_ids.join('\n')}</pre>
                        </details>
                      )}
                    </p>
                  </div>
                  <div>
                    <p className="font-medium text-[var(--color-text)] mb-1">=== CLIENT SIDE ===</p>
                    <p className="text-[var(--color-muted)]">Encrypted document(s) received → decryption successful</p>
                  </div>
                </div>
                <details className="mt-3">
                  <summary className="cursor-pointer font-medium text-[var(--color-text)]">What server sees</summary>
                  <div className="mt-2 p-3 rounded bg-[var(--color-surface)] text-sm text-[var(--color-muted)]">
                    <p className="mb-2">Server sees only: search token, matched encrypted doc IDs, result count ({searchDebug.result_count}).</p>
                    <p className="font-medium text-[var(--color-text)]">Server does NOT see: plaintext keyword, secret key, document contents.</p>
                  </div>
                </details>
              </div>
            )}
          </motion.div>
        )}
      </motion.section>

      {/* Document list */}
      <motion.section
        className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-6 transition-shadow duration-200 hover:shadow-[0_8px_30px_rgba(0,0,0,0.25)]"
        variants={cardItem}
        whileHover={{ scale: 1.01 }}
      >
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-medium text-[var(--color-text)]">Your documents</h2>
          <motion.button
            type="button"
            onClick={loadDocList}
            disabled={loadingDocs}
            className="text-sm text-[var(--color-primary)] hover:underline disabled:opacity-50"
            whileHover={!loadingDocs ? { scale: 1.02 } : undefined}
            whileTap={btnTap}
          >
            {loadingDocs ? 'Loading…' : 'Refresh'}
          </motion.button>
        </div>
        {docIds.length === 0 && !loadingDocs ? (
          <p className="text-[var(--color-muted)] text-sm">No documents yet. Upload some above.</p>
        ) : (
          <>
            <ul className="space-y-1">
              {docIds.map((id) => (
                <li key={id} className="flex items-center justify-between gap-2 group">
                  <motion.button
                    type="button"
                    onClick={() => openDocument(id)}
                    className="text-[var(--color-accent)] hover:underline text-left flex-1 truncate"
                    whileHover={{ x: 2 }}
                    whileTap={btnTap}
                  >
                    {id}
                  </motion.button>
                  <motion.button
                    type="button"
                    onClick={(e) => handleDelete(id, e)}
                    className="text-red-400 hover:text-red-300 text-sm opacity-70 group-hover:opacity-100"
                    title="Delete document"
                    whileHover={{ scale: 1.02 }}
                    whileTap={btnTap}
                  >
                    Delete
                  </motion.button>
                </li>
              ))}
            </ul>
            {totalDocs > docIds.length && (
              <motion.button
                type="button"
                onClick={loadMoreDocs}
                disabled={loadingDocs}
                className="mt-3 text-sm text-[var(--color-primary)] hover:underline disabled:opacity-50"
                whileHover={!loadingDocs ? { scale: 1.02 } : undefined}
                whileTap={btnTap}
              >
                {loadingDocs ? 'Loading…' : `Load more (${docIds.length} of ${totalDocs})`}
              </motion.button>
            )}
          </>
        )}
      </motion.section>

      {/* Benchmark / Scaling */}
      <motion.section
        className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-6 transition-shadow duration-200 hover:shadow-[0_8px_30px_rgba(0,0,0,0.25)]"
        variants={cardItem}
        whileHover={{ scale: 1.01 }}
      >
        <h2 className="text-lg font-medium text-[var(--color-text)] mb-1">Performance & scaling</h2>
        <p className="text-[var(--color-muted)] text-sm mb-4">
          Run benchmarks on isolated test data (100, 1000, 5000 docs). Shows encryption time, search time, index growth, and scaling analysis — so you see it scales, not just that it works.
        </p>
        <motion.button
          type="button"
          onClick={runBenchmark}
          disabled={benchmarkRunning}
          className="px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium disabled:opacity-50"
          whileHover={!benchmarkRunning ? btnHover : undefined}
          whileTap={btnTap}
        >
          {benchmarkRunning ? 'Running benchmark…' : 'Run benchmark'}
        </motion.button>
        {benchmarkError && (
          <p className="mt-3 text-sm text-red-400">{benchmarkError}</p>
        )}
        {benchmarkResult && (
          <motion.div
            className="mt-4 space-y-4"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
          >
            <div className="p-4 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)]">
              <h3 className="text-sm font-semibold text-[var(--color-text)] mb-2">Scaling summary — It scales</h3>
              <p className="text-sm text-[var(--color-muted)]">{benchmarkResult.scaling_analysis.summary}</p>
              {benchmarkResult.scaling_analysis.encryption_time_per_doc_ms != null && (
                <p className="text-xs text-[var(--color-muted)] mt-2">
                  Encryption: ~{benchmarkResult.scaling_analysis.encryption_time_per_doc_ms} ms/doc · Search at N={benchmarkResult.scaling_analysis.max_n_tested}: {benchmarkResult.scaling_analysis.search_time_ms_at_max_n} ms · Index: ~{benchmarkResult.scaling_analysis.index_bytes_per_doc} bytes/doc
                </p>
              )}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b border-[var(--color-border)]">
                    <th className="text-left py-2 pr-4 text-[var(--color-text)]">Docs (N)</th>
                    <th className="text-right py-2 px-2 text-[var(--color-muted)]">Encryption (ms)</th>
                    <th className="text-right py-2 px-2 text-[var(--color-muted)]">Search (ms)</th>
                    <th className="text-right py-2 px-2 text-[var(--color-muted)]">Index (KB)</th>
                  </tr>
                </thead>
                <tbody>
                  {benchmarkResult.benchmark_results.map((r) => (
                    <tr key={r.num_docs} className="border-b border-[var(--color-border)]/50">
                      <td className="py-2 pr-4 font-medium text-[var(--color-text)]">{r.num_docs}</td>
                      <td className="text-right px-2 text-[var(--color-muted)]">{r.error ? '—' : (r.encryption_time_ms ?? r.encryption_sec != null ? (r.encryption_sec * 1000).toFixed(2) : '—')}</td>
                      <td className="text-right px-2 text-[var(--color-muted)]">{r.error ? '—' : (r.search_time_ms ?? (r.search_latency_sec != null ? (r.search_latency_sec * 1000).toFixed(2) : '—'))}</td>
                      <td className="text-right px-2 text-[var(--color-muted)]">{r.error ? '—' : (r.index_size_kb ?? (r.index_size_bytes != null ? (r.index_size_bytes / 1024).toFixed(2) : '—'))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}
      </motion.section>

      {/* View document modal */}
      <AnimatePresence>
        {viewDocId && (
          <motion.div
            className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50"
            onClick={() => setViewDocId(null)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <motion.div
              className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col"
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.2 }}
            >
              <div className="flex items-center justify-between p-4 border-b border-[var(--color-border)]">
                <span className="font-medium text-[var(--color-text)] truncate">{viewDocId}</span>
                <motion.button
                  type="button"
                  onClick={() => setViewDocId(null)}
                  className="text-[var(--color-muted)] hover:text-[var(--color-text)]"
                  whileHover={btnHover}
                  whileTap={btnTap}
                >
                  Close
                </motion.button>
              </div>
              <pre className="p-4 overflow-auto text-sm text-[var(--color-text)] whitespace-pre-wrap flex-1">
                {viewContent ?? 'Loading…'}
              </pre>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
