/**
 * Client-side string encryption/decryption for Locate Encrypted File and Decrypt File Name.
 * Uses AES-256-GCM; format matches backend (nonce || ciphertext || tag), base64url.
 * No dependency on SSE or document storage — purely local string transform.
 */

const GCM_NONCE_BYTES = 12
const GCM_TAG_BYTES = 16

function base64UrlToBytes(b64: string): Uint8Array {
  let s = b64.replace(/-/g, '+').replace(/_/g, '/')
  const pad = 4 - (s.length % 4)
  if (pad !== 4) s += '='.repeat(pad)
  const binary = atob(s)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes
}

function bytesToBase64Url(bytes: Uint8Array): string {
  let binary = ''
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i])
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export async function encryptString(plaintext: string, keyBase64: string): Promise<string> {
  const keyBytes = base64UrlToBytes(keyBase64)
  const key = await crypto.subtle.importKey(
    'raw',
    keyBytes as BufferSource,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt']
  )
  const nonce = crypto.getRandomValues(new Uint8Array(GCM_NONCE_BYTES))
  const encoded = new TextEncoder().encode(plaintext)
  const ciphertext = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv: nonce, tagLength: 128 },
    key,
    encoded
  )
  const combined = new Uint8Array(nonce.length + ciphertext.byteLength)
  combined.set(nonce, 0)
  combined.set(new Uint8Array(ciphertext), nonce.length)
  return bytesToBase64Url(combined)
}

export async function decryptString(ciphertextBase64: string, keyBase64: string): Promise<string> {
  const keyBytes = base64UrlToBytes(keyBase64)
  const key = await crypto.subtle.importKey(
    'raw',
    keyBytes as BufferSource,
    { name: 'AES-GCM', length: 256 },
    false,
    ['decrypt']
  )
  const combined = base64UrlToBytes(ciphertextBase64)
  if (combined.length < GCM_NONCE_BYTES + GCM_TAG_BYTES) {
    throw new Error('Invalid encrypted string: too short')
  }
  const nonce = combined.slice(0, GCM_NONCE_BYTES)
  const ciphertext = combined.slice(GCM_NONCE_BYTES)
  const decrypted = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: nonce as BufferSource, tagLength: 128 },
    key,
    ciphertext as BufferSource
  )
  return new TextDecoder().decode(decrypted)
}
