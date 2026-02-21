"""
Vault-grade file encryption (Cryptomator-inspired).

- AES-256-GCM only; 96-bit random IV per file.
- Authenticated encryption: auth tag verified before decryption.
- Optional metadata_hash for additional integrity (e.g. HMAC of length/type).
- Secure randomness via os.urandom; constant-time comparison where applicable.
- Fail securely on decryption error (no silent swallowing).
"""

import os
import hmac
import hashlib
from typing import Optional, Tuple

try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Random import get_random_bytes
except ImportError:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes

# GCM: 96-bit nonce recommended (NIST); 16-byte tag
GCM_NONCE_SIZE = 12
GCM_TAG_SIZE = 16
METADATA_HASH_SIZE = 32


def encrypt_file_content(plaintext: bytes, k_file_enc: bytes, metadata: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Encrypt file content with AES-256-GCM.
    Uses 96-bit random nonce; produces ciphertext and 16-byte tag.
    Optional: HMAC-SHA256(metadata) appended for integrity (metadata not secret).
    Returns (ciphertext_with_tag, nonce). Caller stores nonce + ciphertext; never reuse nonce.
    """
    if len(k_file_enc) != 32:
        raise ValueError("K_file_enc must be 32 bytes")
    nonce = get_random_bytes(GCM_NONCE_SIZE)
    cipher = AES.new(k_file_enc, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    payload = ciphertext + tag
    if metadata is not None:
        meta_hmac = hmac.new(k_file_enc, metadata, hashlib.sha256).digest()
        payload = payload + meta_hmac
    return payload, nonce


def decrypt_file_content(
    nonce: bytes, payload: bytes, k_file_enc: bytes, metadata: Optional[bytes] = None
) -> bytes:
    """
    Decrypt and verify. Payload = ciphertext || tag [|| metadata_hmac].
    Fails with exception on verification failure (no silent failure).
    """
    if len(k_file_enc) != 32:
        raise ValueError("K_file_enc must be 32 bytes")
    if len(nonce) != GCM_NONCE_SIZE:
        raise ValueError("Nonce must be 12 bytes")
    has_meta = metadata is not None
    if has_meta:
        if len(payload) < GCM_TAG_SIZE + METADATA_HASH_SIZE:
            raise ValueError("Payload too short for tag and metadata hash")
        payload, meta_hmac_stored = payload[:-METADATA_HASH_SIZE], payload[-METADATA_HASH_SIZE:]
        expected_meta = hmac.new(k_file_enc, metadata, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_meta, meta_hmac_stored):
            raise ValueError("Metadata integrity check failed")
    if len(payload) < GCM_TAG_SIZE:
        raise ValueError("Payload too short")
    ciphertext, tag = payload[:-GCM_TAG_SIZE], payload[-GCM_TAG_SIZE:]
    cipher = AES.new(k_file_enc, AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag)


def encrypt_file_payload(plaintext: bytes, k_file_enc: bytes) -> bytes:
    """
    Single blob for server storage: nonce (12) || tag (16) || ciphertext.
    Optional metadata_hash can be added by caller if needed.
    """
    payload, nonce = encrypt_file_content(plaintext, k_file_enc, metadata=None)
    return nonce + payload


def decrypt_file_payload(blob: bytes, k_file_enc: bytes) -> bytes:
    """Decrypt blob = nonce (12) || ciphertext || tag (16)."""
    if len(blob) < GCM_NONCE_SIZE + GCM_TAG_SIZE:
        raise ValueError("Blob too short")
    nonce = blob[:GCM_NONCE_SIZE]
    payload = blob[GCM_NONCE_SIZE:]
    return decrypt_file_content(nonce, payload, k_file_enc, metadata=None)


# Optional alias for metadata-aware storage (e.g. padded size)
def build_metadata_hash(k_file_enc: bytes, file_size: int, extra: bytes = b"") -> bytes:
    """Build HMAC for metadata integrity (size, extra). Not secret."""
    data = file_size.to_bytes(8, "big") + extra
    return hmac.new(k_file_enc, data, hashlib.sha256).digest()
