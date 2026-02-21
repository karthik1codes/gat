/**
 * Locate Encrypted File & Decrypt File Name — client-side only.
 * Step-by-step flow to match reference: Choose a file → Select File Inside Vault → Open → Encrypted path.
 * No dependency on SSE or document upload.
 */

import { useState, useCallback, useRef } from 'react'
import { motion } from 'framer-motion'
import { vaultApi } from '../api/client'
import { encryptString, decryptString } from '../lib/clientStringCrypto'

type LocateStep = 'choose' | 'select' | 'result'

export default function LocateDecryptTools() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [locateStep, setLocateStep] = useState<LocateStep>('choose')
  const [chosenFiles, setChosenFiles] = useState<File[]>([])
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null)
  const [encryptedPath, setEncryptedPath] = useState<string | null>(null)
  const [decryptOpen, setDecryptOpen] = useState(false)
  const [decryptInput, setDecryptInput] = useState('')
  const [decryptResult, setDecryptResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState<string | null>(null)

  const getKey = useCallback(async (): Promise<string> => {
    const { key_base64 } = await vaultApi.getClientStringKey()
    return key_base64
  }, [])

  // Step 1: User clicks "Locate Encrypted File" → open native "Choose a file" dialog
  const openFilePicker = () => {
    setError(null)
    setChosenFiles([])
    setSelectedFileName(null)
    setEncryptedPath(null)
    setLocateStep('choose')
    fileInputRef.current?.click()
  }

  // Step 2: User selected file(s) → show "Select File Inside Vault" modal
  const onFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files?.length) return
    const list = Array.from(files)
    setChosenFiles(list)
    setSelectedFileName(list[0]?.name ?? null)
    setLocateStep('select')
    e.target.value = ''
  }

  // Step 3 → 4: User clicks Open → encrypt filename client-side → show encrypted path
  const handleOpenInVault = async () => {
    const name = selectedFileName ?? chosenFiles[0]?.name
    if (!name) return
    setError(null)
    setEncryptedPath(null)
    setLoading(true)
    try {
      const key = await getKey()
      const encrypted = await encryptString(name, key)
      setEncryptedPath(encrypted)
      setLocateStep('result')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Encryption failed. Is the vault unlocked?')
    } finally {
      setLoading(false)
    }
  }

  const closeLocateModal = () => {
    setLocateStep('choose')
    setChosenFiles([])
    setSelectedFileName(null)
    setEncryptedPath(null)
    setError(null)
  }

  const openDecrypt = () => {
    setDecryptInput('')
    setDecryptResult(null)
    setError(null)
    setDecryptOpen(true)
  }

  const handleDecrypt = async () => {
    const text = decryptInput.trim()
    if (!text) return
    setError(null)
    setDecryptResult(null)
    setLoading(true)
    try {
      const key = await getKey()
      const decrypted = await decryptString(text, key)
      setDecryptResult(decrypted)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Decryption failed. Is the vault unlocked? Is the input valid?')
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = (value: string, label: string) => {
    navigator.clipboard.writeText(value)
    setCopied(label)
    setTimeout(() => setCopied(null), 2000)
  }

  const showSelectFileModal = locateStep === 'select' || locateStep === 'result'

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="sr-only"
        aria-hidden
        onChange={onFileSelected}
      />
      <motion.div className="flex flex-wrap gap-4 mt-8 p-4 rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)]/30" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.25 }}>
        <motion.button
          type="button"
          onClick={openFilePicker}
          title="Choose a file"
          className="flex flex-col items-center justify-center min-w-[180px] py-4 px-4 rounded-lg border border-dashed border-[var(--color-border)] bg-[var(--color-bg)] hover:bg-[var(--color-surface)] transition-colors duration-200 text-left"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <span className="text-sm font-mono text-[var(--color-muted)] mb-2">abc → 101010</span>
          <span className="text-sm font-medium text-[var(--color-text)]">Locate Encrypted File</span>
        </motion.button>
        <motion.button
          type="button"
          onClick={openDecrypt}
          className="flex flex-col items-center justify-center min-w-[180px] py-4 px-4 rounded-lg border border-dashed border-[var(--color-border)] bg-[var(--color-bg)] hover:bg-[var(--color-surface)] transition-colors duration-200 text-left"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <span className="text-sm font-mono text-[var(--color-muted)] mb-2">101010 → abc</span>
          <span className="text-sm font-medium text-[var(--color-text)]">Decrypt File Name</span>
        </motion.button>
      </motion.div>

      {/* Step 2 & 4: "Select File Inside Vault" modal — file list, File name, Open/Cancel → then Encrypted path */}
      {showSelectFileModal && (
        <motion.div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50" onClick={closeLocateModal} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
          <motion.div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl max-w-lg w-full shadow-xl overflow-hidden flex flex-col max-h-[85vh]" onClick={e => e.stopPropagation()} initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.96 }} transition={{ duration: 0.2 }}>
            <div className="p-4 border-b border-[var(--color-border)] shrink-0">
              <h3 className="text-lg font-medium text-[var(--color-text)]">Select File Inside Vault</h3>
            </div>
            <div className="p-4 overflow-auto flex-1 min-h-0">
              {locateStep === 'result' ? (
                <>
                  {error && <p className="text-red-400 text-sm mb-2">{error}</p>}
                  {encryptedPath && (
                    <div className="space-y-3">
                      <p className="text-sm text-[var(--color-muted)]">Encrypted path for this file:</p>
                      <div className="flex gap-2">
                        <code className="flex-1 px-3 py-2 rounded-lg bg-[var(--color-bg)] text-sm text-[var(--color-text)] break-all border border-[var(--color-border)]">
                          {encryptedPath}
                        </code>
                        <button
                          type="button"
                          onClick={() => copyToClipboard(encryptedPath, 'locate')}
                          className="shrink-0 px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white text-sm font-medium"
                        >
                          {copied === 'locate' ? 'Copied' : 'Copy path'}
                        </button>
                      </div>
                      <p className="text-xs text-[var(--color-muted)]">This is the client-side encrypted form of the file name. Copy to use as encrypted path or identifier.</p>
                    </div>
                  )}
                </>
              ) : chosenFiles.length === 0 ? (
                <p className="text-sm text-[var(--color-muted)]">No file selected. Use &quot;Choose a file&quot; to select a file.</p>
              ) : (
                <>
                  <div className="rounded-lg border border-[var(--color-border)] overflow-hidden mb-4">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="bg-[var(--color-bg)] border-b border-[var(--color-border)]">
                          <th className="px-3 py-2 font-medium text-[var(--color-muted)]">Name</th>
                          <th className="px-3 py-2 font-medium text-[var(--color-muted)] w-24">Type</th>
                        </tr>
                      </thead>
                      <tbody>
                        {chosenFiles.map(file => (
                          <tr
                            key={`${file.name}-${file.size}`}
                            onClick={() => setSelectedFileName(file.name)}
                            className={`border-b border-[var(--color-border)] last:border-b-0 cursor-pointer ${selectedFileName === file.name ? 'bg-[var(--color-primary)]/15' : 'hover:bg-[var(--color-bg)]'}`}
                          >
                            <td className="px-3 py-2 text-[var(--color-text)]">{file.name}</td>
                            <td className="px-3 py-2 text-[var(--color-muted)]">{file.type || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <label className="block text-sm font-medium text-[var(--color-muted)] mb-1">File name:</label>
                  <div className="px-3 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] mb-4 text-sm">
                    {selectedFileName ?? '—'}
                  </div>
                  {error && <p className="text-red-400 text-sm mb-2">{error}</p>}
                </>
              )}
            </div>
            <div className="p-4 border-t border-[var(--color-border)] flex justify-end gap-2 shrink-0">
              {locateStep === 'result' ? (
                <>
                  <button type="button" onClick={() => { setLocateStep('select'); setEncryptedPath(null); setError(null) }} className="px-4 py-2 rounded-lg border border-[var(--color-border)] text-[var(--color-text)]">
                    Back
                  </button>
                  <button type="button" onClick={closeLocateModal} className="px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium">
                    Close
                  </button>
                </>
              ) : (
                <>
                  <button type="button" onClick={closeLocateModal} className="px-4 py-2 rounded-lg border border-[var(--color-border)] text-[var(--color-text)]">
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleOpenInVault}
                    disabled={loading || !selectedFileName}
                    className="px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium disabled:opacity-50"
                  >
                    {loading ? 'Encrypting…' : 'Open'}
                  </button>
                </>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}

      {/* Decrypt File Name modal */}
      {decryptOpen && (
        <motion.div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50" onClick={() => setDecryptOpen(false)} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
          <motion.div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl max-w-lg w-full p-6 shadow-xl" onClick={e => e.stopPropagation()} initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.96 }} transition={{ duration: 0.2 }}>
            <h3 className="text-lg font-medium text-[var(--color-text)] mb-2">Decrypt File Name</h3>
            <p className="text-sm text-[var(--color-muted)] mb-4">
              Paste an encrypted string (from Locate Encrypted File). It will be decrypted on your device only.
            </p>
            <label className="block text-sm font-medium text-[var(--color-text)] mb-2">Encrypted string:</label>
            <textarea
              value={decryptInput}
              onChange={e => setDecryptInput(e.target.value)}
              placeholder="Paste base64url encrypted value"
              rows={3}
              className="w-full px-3 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] placeholder-[var(--color-muted)] mb-4 font-mono text-sm"
            />
            {error && <p className="text-red-400 text-sm mb-2">{error}</p>}
            {decryptResult !== null && (
              <div className="space-y-2 mb-4">
                <label className="block text-xs font-medium text-[var(--color-muted)]">Original:</label>
                <div className="flex gap-2 items-center">
                  <code className="flex-1 px-3 py-2 rounded-lg bg-[var(--color-bg)] text-sm text-[var(--color-text)] border border-[var(--color-border)]">
                    {decryptResult}
                  </code>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(decryptResult, 'decrypt')}
                    className="shrink-0 px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white text-sm font-medium"
                  >
                    {copied === 'decrypt' ? 'Copied' : 'Copy'}
                  </button>
                </div>
              </div>
            )}
            <div className="flex justify-end gap-2 mt-4">
              <button type="button" onClick={() => setDecryptOpen(false)} className="px-4 py-2 rounded-lg border border-[var(--color-border)] text-[var(--color-text)]">
                Close
              </button>
              <button type="button" onClick={handleDecrypt} disabled={loading || !decryptInput.trim()} className="px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white font-medium disabled:opacity-50">
                {loading ? 'Decrypting…' : 'Decrypt'}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </>
  )
}
