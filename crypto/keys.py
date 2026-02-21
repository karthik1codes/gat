"""
Secure key management for SSE.

- HKDF (RFC 5869) key derivation from a single master key.
- Separate key domains: K_enc (document encryption), K_search (trapdoors), K_index (index encoding).
- Keys are never stored on the server; only key identifiers (e.g. user_id) partition data.
- Uses os.urandom for master key generation; no hardcoded keys.
"""

import os
import hmac
import hashlib
from typing import NamedTuple

# Key sizes (bytes). AES-256 and HMAC-SHA256 both use 32-byte keys.
MASTER_KEY_SIZE = 32
DERIVED_KEY_SIZE = 32
HKDF_HASH = hashlib.sha256

# Labels for HKDF-Expand; distinct to ensure independent keys.
LABEL_K_ENC = b"sse.v1.k_enc"
LABEL_K_SEARCH = b"sse.v1.k_search"
LABEL_K_INDEX = b"sse.v1.k_index"


class KeyBundle(NamedTuple):
    """Derived key set. Client holds this; server never sees any key material."""
    k_enc: bytes      # Document encryption (AES-256-GCM)
    k_search: bytes   # Search token (trapdoor) generation
    k_index: bytes    # Index entry encoding (keyword -> index key)


def _hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    """HKDF-Extract: PRK = HMAC-Hash(salt, IKM). Salt can be empty."""
    return hmac.new(salt, ikm, HKDF_HASH).digest()


def _hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    """HKDF-Expand: output length bytes from PRK and info."""
    n = (length + HKDF_HASH().digest_size - 1) // HKDF_HASH().digest_size
    if n > 255:
        raise ValueError("HKDF-Expand length too large")
    out = b""
    t = b""
    for i in range(1, n + 1):
        t = hmac.new(prk, t + info + bytes([i]), HKDF_HASH).digest()
        out += t
    return out[:length]


def hkdf_derive(master_key: bytes, info: bytes, length: int = DERIVED_KEY_SIZE) -> bytes:
    """
    Derive a single key from master_key using HKDF.
    Uses empty salt (OK when master_key is high-entropy).
    """
    prk = _hkdf_extract(b"", master_key)
    return _hkdf_expand(prk, info, length)


def generate_master_key() -> bytes:
    """Generate a new 256-bit master key using os.urandom. No hardcoded keys."""
    return os.urandom(MASTER_KEY_SIZE)


def derive_key_bundle(master_key: bytes) -> KeyBundle:
    """
    Derive K_enc, K_search, K_index from master key via HKDF.
    Each key is cryptographically independent; compromise of one does not reveal others.
    """
    if len(master_key) < MASTER_KEY_SIZE:
        raise ValueError("Master key must be at least 32 bytes")
    return KeyBundle(
        k_enc=hkdf_derive(master_key, LABEL_K_ENC),
        k_search=hkdf_derive(master_key, LABEL_K_SEARCH),
        k_index=hkdf_derive(master_key, LABEL_K_INDEX),
    )


def key_identifier(master_key: bytes) -> bytes:
    """
    Produce a non-reversible identifier for the key domain (e.g. for server-side partitioning).
    Server stores only this; never the key. Uses SHA-256 so key material is not exposed.
    """
    return hashlib.sha256(master_key).digest()


def constant_time_equals(a: bytes, b: bytes) -> bool:
    """Constant-time comparison to prevent timing leaks on token/trapdoor comparison."""
    return hmac.compare_digest(a, b)
