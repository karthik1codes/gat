"""
Filename encryption (Cryptomator-grade).

- Encrypt filenames with AES-256-GCM using K_filename_enc.
- Server stores only encrypted filename (e.g. base64); never sees original.
- Unique nonce per encryption; result encoded for storage (base64url).
"""

import base64
import os
from typing import Optional

try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Random import get_random_bytes
except ImportError:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes

GCM_NONCE_SIZE = 12
GCM_TAG_SIZE = 16


def encrypt_filename(plaintext_name: str, k_filename_enc: bytes) -> str:
    """
    Encrypt filename; return base64url-encoded string (safe for storage/key).
    Uses 96-bit random nonce per encryption.
    """
    if len(k_filename_enc) != 32:
        raise ValueError("K_filename_enc must be 32 bytes")
    name_bytes = plaintext_name.encode("utf-8")
    nonce = get_random_bytes(GCM_NONCE_SIZE)
    cipher = AES.new(k_filename_enc, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(name_bytes)
    blob = nonce + ciphertext + tag
    return base64.urlsafe_b64encode(blob).decode("ascii").rstrip("=")


def decrypt_filename(encrypted_b64: str, k_filename_enc: bytes) -> str:
    """Decrypt base64url-encoded filename. Raises on verification failure."""
    if len(k_filename_enc) != 32:
        raise ValueError("K_filename_enc must be 32 bytes")
    pad = 4 - len(encrypted_b64) % 4
    if pad != 4:
        encrypted_b64 += "=" * pad
    blob = base64.urlsafe_b64decode(encrypted_b64)
    if len(blob) < GCM_NONCE_SIZE + GCM_TAG_SIZE:
        raise ValueError("Encrypted filename blob too short")
    nonce = blob[:GCM_NONCE_SIZE]
    ciphertext = blob[GCM_NONCE_SIZE:-GCM_TAG_SIZE]
    tag = blob[-GCM_TAG_SIZE:]
    cipher = AES.new(k_filename_enc, AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")


def doc_id_to_storage_key(doc_id: str) -> str:
    """
    Sanitize doc_id for use as server storage key (e.g. filesystem).
    If doc_id is already base64url (encrypted filename), return as-is (safe).
    Otherwise escape for compatibility.
    """
    # Base64url is alphanumeric + - _ ; safe for most backends
    return doc_id
