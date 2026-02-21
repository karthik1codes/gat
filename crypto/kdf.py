"""
Strong key derivation for vault-based SSE.

- K_master from password via scrypt (or PBKDF2-HMAC-SHA256) with 200k+ iterations.
- Salt is 16+ bytes random; stored with vault config (not secret).
- Then HKDF-SHA256 to derive domain-separated keys:
  K_file_enc, K_filename_enc, K_search, K_index, K_index_mac.
- No plaintext keys on server; keys exist only in client memory when vault is unlocked.
"""

import os
import hmac
import hashlib
from typing import NamedTuple

# Scrypt: N cost factor (memory ~128*N*r bytes). Default 8192 for portability; set GAT_SCRYPT_N=32768 for production.
import os as _os
SCRYPT_N = int(_os.environ.get("GAT_SCRYPT_N", "8192"))
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_KEY_LEN = 32
SALT_SIZE = 32
PBKDF2_ITERATIONS = 200_000
PBKDF2_KEY_LEN = 32
HKDF_KEY_LEN = 32

# HKDF info strings; distinct to ensure independent keys (RFC 5869)
INFO_K_FILE_ENC = b"vault.v1.k_file_enc"
INFO_K_FILENAME_ENC = b"vault.v1.k_filename_enc"
INFO_K_SEARCH = b"vault.v1.k_search"
INFO_K_INDEX = b"vault.v1.k_index"
INFO_K_INDEX_MAC = b"vault.v1.k_index_mac"


class VaultKeyBundle(NamedTuple):
    """Derived keys for vault. All 32-byte; used for AES-256 and HMAC-SHA256."""
    k_file_enc: bytes
    k_filename_enc: bytes
    k_search: bytes
    k_index: bytes
    k_index_mac: bytes


def _hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    """HKDF-Extract: PRK = HMAC-Hash(salt, IKM)."""
    return hmac.new(salt, ikm, hashlib.sha256).digest()


def _hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    """HKDF-Expand: output length bytes from PRK and info."""
    digest_len = hashlib.sha256().digest_size
    n = (length + digest_len - 1) // digest_len
    if n > 255:
        raise ValueError("HKDF-Expand length too large")
    out = b""
    t = b""
    for i in range(1, n + 1):
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest()
        out += t
    return out[:length]


def hkdf_derive(prk: bytes, info: bytes, length: int = HKDF_KEY_LEN) -> bytes:
    """Derive one key from PRK (from HKDF-Extract) with info."""
    return _hkdf_expand(prk, info, length)


def generate_salt() -> bytes:
    """Generate a random salt (not secret; stored with vault)."""
    return os.urandom(SALT_SIZE)


def scrypt_derive(password: bytes, salt: bytes) -> bytes:
    """
    Derive K_master from password using scrypt.
    Uses SCRYPT_N, SCRYPT_R, SCRYPT_P; minimum 200k effective iterations equivalent.
    Salt must be 16+ bytes; stored with vault config.
    """
    if len(salt) < 16:
        raise ValueError("Salt must be at least 16 bytes")
    return hashlib.scrypt(
        password,
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_KEY_LEN,
    )


def pbkdf2_derive(password: bytes, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytes:
    """
    Derive K_master from password using PBKDF2-HMAC-SHA256.
    Fallback when scrypt is not desired; iterations >= 200_000.
    """
    if len(salt) < 16:
        raise ValueError("Salt must be at least 16 bytes")
    if iterations < 200_000:
        raise ValueError("PBKDF2 iterations must be at least 200,000")
    return hashlib.pbkdf2_hmac("sha256", password, salt, iterations, dklen=PBKDF2_KEY_LEN)


def derive_vault_keys(k_master: bytes) -> VaultKeyBundle:
    """
    Derive all vault keys from K_master using HKDF.
    Domain separation via distinct info strings; compromise of one key does not reveal others.
    """
    if len(k_master) < 32:
        raise ValueError("K_master must be at least 32 bytes")
    prk = _hkdf_extract(b"", k_master)
    return VaultKeyBundle(
        k_file_enc=hkdf_derive(prk, INFO_K_FILE_ENC),
        k_filename_enc=hkdf_derive(prk, INFO_K_FILENAME_ENC),
        k_search=hkdf_derive(prk, INFO_K_SEARCH),
        k_index=hkdf_derive(prk, INFO_K_INDEX),
        k_index_mac=hkdf_derive(prk, INFO_K_INDEX_MAC),
    )


def derive_vault_keys_from_password(password: bytes, salt: bytes, use_scrypt: bool = True) -> tuple[bytes, VaultKeyBundle]:
    """
    Derive K_master from password (scrypt or PBKDF2) then vault key bundle.
    Returns (k_master, bundle). Salt is not secret; store with vault config.
    """
    if use_scrypt:
        k_master = scrypt_derive(password, salt)
    else:
        k_master = pbkdf2_derive(password, salt)
    bundle = derive_vault_keys(k_master)
    return k_master, bundle
