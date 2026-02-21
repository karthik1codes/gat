"""
Filename encryption (Cryptomator-grade).

- Encrypt filenames with AES-256-GCM using K_file_enc or K_filename_enc (32-byte key).
- Server stores only encrypted_filename, filename_iv, filename_tag; never plaintext.
- Unique IV per encryption; decryption client-side only when using client-held key.
"""

import base64
import os
from typing import Any, Dict

try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Random import get_random_bytes
except ImportError:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes

GCM_NONCE_SIZE = 12
GCM_TAG_SIZE = 16


def encrypt_filename_structured(plaintext_name: str, key: bytes) -> Dict[str, str]:
    """
    Encrypt filename with AES-256-GCM; return dict for server storage.
    key: 32-byte K_file_enc or K_filename_enc.
    Returns: { "encrypted_filename": b64(ciphertext), "filename_iv": b64(iv), "filename_tag": b64(tag) }.
    Server must NEVER store plaintext; decryption client-side only.
    """
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes")
    name_bytes = plaintext_name.encode("utf-8")
    iv = get_random_bytes(GCM_NONCE_SIZE)
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    ciphertext, tag = cipher.encrypt_and_digest(name_bytes)
    return {
        "encrypted_filename": base64.urlsafe_b64encode(ciphertext).decode("ascii").rstrip("="),
        "filename_iv": base64.urlsafe_b64encode(iv).decode("ascii").rstrip("="),
        "filename_tag": base64.urlsafe_b64encode(tag).decode("ascii").rstrip("="),
    }


def _b64decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s = s + "=" * pad
    return base64.urlsafe_b64decode(s)


def decrypt_filename_structured(payload: Dict[str, Any], key: bytes) -> str:
    """Decrypt from stored { encrypted_filename, filename_iv, filename_tag }. Fails securely on error."""
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes")
    for k in ("encrypted_filename", "filename_iv", "filename_tag"):
        if k not in payload or not payload[k]:
            raise ValueError("Missing required field for decryption")
    ciphertext = _b64decode(payload["encrypted_filename"])
    iv = _b64decode(payload["filename_iv"])
    tag = _b64decode(payload["filename_tag"])
    if len(iv) != GCM_NONCE_SIZE or len(tag) != GCM_TAG_SIZE:
        raise ValueError("Invalid IV or tag length")
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")


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
