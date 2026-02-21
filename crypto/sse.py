"""
Searchable Symmetric Encryption (SSE) primitives.

- Document encryption: AES-256-GCM with random IV per document (authenticated encryption).
- Key usage: K_enc (documents), K_search (trapdoors), K_index (index encoding) derived via HKDF from master key.
- Trapdoor/index: HMAC-SHA256 with K_search/K_index; server matches without seeing plaintext.
- Secure randomness: os.urandom / get_random_bytes for IVs; no deterministic IVs.
"""

from typing import Tuple

try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Hash import HMAC, SHA256
    from Cryptodome.Random import get_random_bytes
except ImportError:
    from Crypto.Cipher import AES
    from Crypto.Hash import HMAC, SHA256
    from Crypto.Random import get_random_bytes

from .keys import derive_key_bundle, generate_master_key, constant_time_equals

# Cipher constants
IV_SIZE = 16
TAG_SIZE = 16
MASTER_KEY_SIZE = 32


def generate_key() -> bytes:
    """Generate a random 256-bit master key. Backward-compatible alias for generate_master_key."""
    return generate_master_key()


def _get_keys(master_key: bytes):
    """Derive key bundle from master key. Used by all operations."""
    return derive_key_bundle(master_key)


def encrypt_document(plaintext: bytes, master_key: bytes) -> Tuple[bytes, bytes]:
    """
    Encrypt document with AES-256-GCM using K_enc.
    Random IV per document; IV is prepended to payload so server never sees plaintext.
    Returns (payload, iv) for storage; payload = iv || tag || ciphertext.
    """
    keys = _get_keys(master_key)
    iv = get_random_bytes(IV_SIZE)
    cipher = AES.new(keys.k_enc, AES.MODE_GCM, nonce=iv)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    payload = iv + tag + ciphertext
    return payload, iv


def decrypt_document(payload: bytes, master_key: bytes) -> bytes:
    """Decrypt a document payload (iv || tag || ciphertext) using K_enc."""
    keys = _get_keys(master_key)
    iv = payload[:IV_SIZE]
    tag = payload[IV_SIZE : IV_SIZE + TAG_SIZE]
    ciphertext = payload[IV_SIZE + TAG_SIZE :]
    cipher = AES.new(keys.k_enc, AES.MODE_GCM, nonce=iv)
    return cipher.decrypt_and_verify(ciphertext, tag)


def build_trapdoor(keyword: str, master_key: bytes) -> bytes:
    """
    Build search trapdoor (token) for a keyword using K_search.
    Server compares this with index keys via constant-time comparison.
    Same keyword -> same trapdoor (deterministic); see forward-privacy module for stronger guarantees.
    """
    keys = _get_keys(master_key)
    w = keyword.strip().lower().encode("utf-8")
    h = HMAC.new(keys.k_search, digestmod=SHA256)
    h.update(w)
    return h.digest()


def encrypt_keyword_for_index(keyword: str, master_key: bytes) -> bytes:
    """
    Deterministic encoding of keyword for index storage.
    Uses K_search so that server can match search token to index entry (token and index key are same function).
    K_index is reserved for future use (e.g. encrypting index payloads).
    """
    return build_trapdoor(keyword, master_key)


def trapdoor_matches(token: bytes, index_key: bytes) -> bool:
    """Constant-time comparison for server-side matching. Prevents timing leaks."""
    if len(token) != len(index_key):
        return False
    return constant_time_equals(token, index_key)
