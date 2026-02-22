import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { performanceApi, type RealPerformanceMetrics } from '../api/client'

const cardItem = { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 } }
const btnTap = { scale: 0.98 }

const CHART_COLOR = 'rgba(139, 92, 246, 0.85)'
const CHART_GRID = 'rgba(255, 255, 255, 0.06)'

export default function PerformancePage() {
  const [metrics, setMetrics] = useState<RealPerformanceMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadMetrics = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await performanceApi.getReal()
      setMetrics(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load metrics')
      setMetrics(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadMetrics()
  }, [loadMetrics])

  if (loading) {
    return (
      <div className="min-h-[200px] flex items-center justify-center">
        <p className="text-[var(--color-muted)]">Loading performance metrics…</p>
      </div>
    )
  }

  if (error) {
    return (
      <motion.div className="space-y-6" initial="initial" animate="animate" variants={{ initial: {}, animate: { transition: { staggerChildren: 0.05 } } }}>
        <motion.div variants={cardItem}>
          <h1 className="text-2xl font-semibold text-[var(--color-text)] mb-1">Performance & scaling</h1>
          <p className="text-red-400 text-sm">{error}</p>
        </motion.div>
      </motion.div>
    )
  }

  const hasDocs = metrics && metrics.document_count > 0
  const hasSearch = metrics && metrics.has_search_result && metrics.last_search_latency_ms != null

  return (
    <motion.div className="space-y-8" initial="initial" animate="animate" variants={{ initial: {}, animate: { transition: { staggerChildren: 0.05, delayChildren: 0.05 } } }}>
      <motion.div variants={cardItem}>
        <h1 className="text-2xl font-semibold text-[var(--color-text)] mb-1">Performance & scaling</h1>
      </motion.div>

      {!hasDocs && (
        <motion.section
          className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-6"
          variants={cardItem}
        >
          <h2 className="text-lg font-medium text-[var(--color-text)] mb-2">No documents yet</h2>
          <p className="text-[var(--color-muted)] text-sm mb-4">
            Performance & scaling is based only on your real data. Upload at least one document, then run a search (keyword, substring, fuzzy, or ranked). After you decrypt a document by viewing it from search results, this page will show your real encryption time, search latency, and index size.
          </p>
          <p className="text-[var(--color-muted)] text-sm">
            Go to <strong className="text-[var(--color-text)]">Documents</strong> to upload files, then search to see metrics here.
          </p>
        </motion.section>
      )}

      {hasDocs && (
        <motion.section
          className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-6 transition-shadow duration-200 hover:shadow-[0_8px_30px_rgba(0,0,0,0.25)]"
          variants={cardItem}
          whileHover={{ scale: 1.01 }}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-[var(--color-text)]">Your real performance</h2>
            <motion.button
              type="button"
              onClick={loadMetrics}
              className="text-sm text-[var(--color-primary)] hover:underline"
              whileTap={btnTap}
            >
              Refresh
            </motion.button>
          </div>
          <p className="text-[var(--color-muted)] text-sm mb-4">
            Index size is read from storage on each refresh. Below: one row per document with index share, encryption time (from last upload that included this doc), and whether it matched the last search.
          </p>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-6">
            <div className="p-4 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)]">
              <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wider">Documents</p>
              <p className="text-xl font-semibold text-[var(--color-text)] mt-1">{metrics!.document_count}</p>
            </div>
            <div className="p-4 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)]">
              <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wider">Index size (total)</p>
              <p className="text-xl font-semibold text-[var(--color-text)] mt-1">{metrics!.index_size_kb} KB</p>
              <p className="text-xs text-[var(--color-muted)] mt-0.5">From current storage</p>
            </div>
            <div className="p-4 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)]">
              <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wider">Last upload</p>
              <p className="text-xl font-semibold text-[var(--color-text)] mt-1">
                {metrics!.last_upload_duration_ms != null
                  ? `${metrics!.last_upload_duration_ms.toFixed(2)} ms`
                  : '—'}
              </p>
              {metrics!.last_upload_doc_count != null && (
                <p className="text-xs text-[var(--color-muted)] mt-0.5">{metrics!.last_upload_doc_count} doc(s)</p>
              )}
            </div>
            <div className="p-4 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)]">
              <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wider">Last search</p>
              <p className="text-xl font-semibold text-[var(--color-text)] mt-1">
                {metrics!.last_search_latency_ms != null
                  ? `${metrics!.last_search_latency_ms.toFixed(2)} ms`
                  : '—'}
              </p>
              {!hasSearch && (
                <p className="text-xs text-[var(--color-muted)] mt-0.5">Run a search to see latency</p>
              )}
            </div>
          </div>

          {/* Per-document graphs: each document has its own bar, no combined totals */}
          {(() => {
            const docs = metrics!.documents || []
            const truncate = (id: string, max = 22) => (id.length > max ? id.slice(0, max - 1) + '…' : id)
            const minChartHeight = 120 + docs.length * 28
            const chartHeight = Math.max(minChartHeight, 220)
            return (
              <>
                {/* Index size per document (KB) - one bar per document */}
                <div className="rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] p-4 mb-6">
                  <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3">Index size per document (KB)</h3>
                  <p className="text-xs text-[var(--color-muted)] mb-2">Each bar is one document; value is that document’s share of the index.</p>
                  <div className="w-full min-w-0" style={{ height: chartHeight }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={docs.map((d) => ({ name: truncate(d.id), fullName: d.id, value: d.index_share_kb }))}
                        layout="vertical"
                        margin={{ top: 4, right: 24, left: 4, bottom: 4 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} horizontal={false} />
                        <XAxis type="number" tick={{ fill: 'var(--color-muted)', fontSize: 11 }} unit=" KB" />
                        <YAxis type="category" dataKey="name" width={140} tick={{ fill: 'var(--color-muted)', fontSize: 11 }} />
                        <Tooltip
                          contentStyle={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 8 }}
                          formatter={(value, _name, props) => [`${Number(value ?? 0)} KB`, (props?.payload as { fullName: string })?.fullName ?? '']}
                        />
                        <Bar dataKey="value" fill={CHART_COLOR} radius={[0, 4, 4, 0]} minPointSize={8} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Search latency per matched document (ms) - one bar per document that matched last search */}
                <div className="rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] p-4 mb-6">
                  <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3">Search latency per matched document (ms)</h3>
                  <p className="text-xs text-[var(--color-muted)] mb-2">One bar per document returned by the last search; value is the same search latency for that query.</p>
                  {hasSearch && docs.some((d) => d.matched_in_last_search) ? (
                    <div className="w-full min-w-0" style={{ height: chartHeight }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={docs
                            .filter((d) => d.matched_in_last_search)
                            .map((d) => ({
                              name: truncate(d.id),
                              fullName: d.id,
                              value: metrics!.last_search_latency_ms ?? 0,
                            }))}
                          layout="vertical"
                          margin={{ top: 4, right: 24, left: 4, bottom: 4 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} horizontal={false} />
                          <XAxis type="number" tick={{ fill: 'var(--color-muted)', fontSize: 11 }} unit=" ms" />
                          <YAxis type="category" dataKey="name" width={140} tick={{ fill: 'var(--color-muted)', fontSize: 11 }} />
                          <Tooltip
                            contentStyle={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 8 }}
                            formatter={(value, _name, props) => [
                              `${Number(value ?? 0).toFixed(2)} ms`,
                              (props?.payload as { fullName: string })?.fullName ?? '',
                            ]}
                          />
                          <Bar dataKey="value" fill={CHART_COLOR} radius={[0, 4, 4, 0]} minPointSize={8} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center text-[var(--color-muted)] text-sm" style={{ minHeight: 120 }}>
                      {hasSearch
                        ? 'No documents matched the last search.'
                        : 'Run a search on Documents to see latency per matched document here.'}
                    </div>
                  )}
                </div>

                {/* Encryption time per document (ms) - one bar per document */}
                {docs.some((d) => d.encryption_ms != null) && (
                  <div className="rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] p-4 mb-6">
                    <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3">Encryption time per document (ms)</h3>
                    <p className="text-xs text-[var(--color-muted)] mb-2">One bar per document; value is encryption time from the last upload that included this doc.</p>
                    <div className="w-full min-w-0" style={{ height: chartHeight }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={docs
                            .filter((d) => d.encryption_ms != null)
                            .map((d) => ({
                              name: truncate(d.id),
                              fullName: d.id,
                              value: d.encryption_ms!,
                            }))}
                          layout="vertical"
                          margin={{ top: 4, right: 24, left: 4, bottom: 4 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} horizontal={false} />
                          <XAxis type="number" tick={{ fill: 'var(--color-muted)', fontSize: 11 }} unit=" ms" />
                          <YAxis type="category" dataKey="name" width={140} tick={{ fill: 'var(--color-muted)', fontSize: 11 }} />
                          <Tooltip
                            contentStyle={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 8 }}
                            formatter={(value, _name, props) => [
                              `${Number(value ?? 0).toFixed(2)} ms`,
                              (props?.payload as { fullName: string })?.fullName ?? '',
                            ]}
                          />
                          <Bar dataKey="value" fill={CHART_COLOR} radius={[0, 4, 4, 0]} minPointSize={8} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}
              </>
            )
          })()}

          <h3 className="text-sm font-semibold text-[var(--color-text)] mb-2">Per document</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-[var(--color-border)]">
                  <th className="text-left py-2 pr-4 text-[var(--color-text)]">Document</th>
                  <th className="text-right py-2 px-2 text-[var(--color-muted)]">Index (KB)</th>
                  <th className="text-right py-2 px-2 text-[var(--color-muted)]">Encryption (ms)</th>
                  <th className="text-center py-2 px-2 text-[var(--color-muted)]">Matched last search</th>
                </tr>
              </thead>
              <tbody>
                {(metrics!.documents || []).map((doc) => (
                  <tr key={doc.id} className="border-b border-[var(--color-border)]/50">
                    <td className="py-2 pr-4 font-medium text-[var(--color-text)] truncate max-w-[200px]" title={doc.id}>{doc.id}</td>
                    <td className="text-right px-2 text-[var(--color-muted)]">{doc.index_share_kb}</td>
                    <td className="text-right px-2 text-[var(--color-muted)]">{doc.encryption_ms != null ? doc.encryption_ms.toFixed(2) : '—'}</td>
                    <td className="text-center px-2 text-[var(--color-muted)]">{doc.matched_in_last_search ? 'Yes' : 'No'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.section>
      )}
    </motion.div>
  )
}
