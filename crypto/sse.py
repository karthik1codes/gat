"""
Searchable Symmetric Encryption (SSE) primitives.

- Key generation (master key; derive encryption and index keys).
- Document encryption/decryption (AES-256-GCM).
- Trapdoor generation for search tokens (HMAC-SHA256).
- Index entry encoding: same deterministic function so server can match token to index.
"""

import hashlib
from typing import Tuple

# Prefer PyCryptodome; fallback to PyCrypto-style API if needed
try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad
    from Cryptodome.Hash import HMAC, SHA256
    from Cryptodome.Random import get_random_bytes
except ImportError:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    from Crypto.Hash import HMAC, SHA256
    from Crypto.Random import get_random_bytes

# Key sizes
MASTER_KEY_SIZE = 32  # 256 bits
IV_SIZE = 16
TAG_SIZE = 16
BLOCK_SIZE = 16


def _derive_key(master_key: bytes, label: str) -> bytes:
    """Derive a key from master key and label using SHA-256."""
    return hashlib.sha256(master_key + label.encode()).digest()


def generate_key() -> bytes:
    """Generate a random 256-bit master key for SSE."""
    return get_random_bytes(MASTER_KEY_SIZE)


def encrypt_document(plaintext: bytes, master_key: bytes) -> Tuple[bytes, bytes]:
    """
    Encrypt document with AES-256-GCM.
    Returns (ciphertext_with_iv_and_tag, iv) for storage.
    Caller typically stores ciphertext; IV is prepended in our format.
    """
    enc_key = _derive_key(master_key, "encrypt")
    iv = get_random_bytes(IV_SIZE)
    cipher = AES.new(enc_key, AES.MODE_GCM, nonce=iv)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    # Store as iv + tag + ciphertext so we can decrypt in one shot
    payload = iv + tag + ciphertext
    return payload, iv


def decrypt_document(payload: bytes, master_key: bytes) -> bytes:
    """Decrypt a document payload (iv + tag + ciphertext)."""
    enc_key = _derive_key(master_key, "encrypt")
    iv = payload[:IV_SIZE]
    tag = payload[IV_SIZE : IV_SIZE + TAG_SIZE]
    ciphertext = payload[IV_SIZE + TAG_SIZE :]
    cipher = AES.new(enc_key, AES.MODE_GCM, nonce=iv)
    return cipher.decrypt_and_verify(ciphertext, tag)


def build_trapdoor(keyword: str, master_key: bytes) -> bytes:
    """
    Build search trapdoor (token) for a keyword.
    Server will compare this with index keys; same keyword -> same trapdoor.
    """
    index_key = _derive_key(master_key, "index")
    # Normalize keyword: lowercase, strip for consistent matching
    w = keyword.strip().lower()
    h = HMAC.new(index_key, digestmod=SHA256)
    h.update(w.encode("utf-8"))
    return h.digest()


def encrypt_keyword_for_index(keyword: str, master_key: bytes) -> bytes:
    """
    Deterministic encoding of keyword for index storage.
    Must match trapdoor so that server can find matches:
    token = build_trapdoor(query) and index key = encrypt_keyword_for_index(keyword).
    We use the same function (trapdoor) for both so they are identical.
    """
    return build_trapdoor(keyword, master_key)
