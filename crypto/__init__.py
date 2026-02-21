"""Cryptographic primitives for Searchable Symmetric Encryption (SSE)."""

from .sse import (
    generate_key,
    encrypt_document,
    decrypt_document,
    build_trapdoor,
    encrypt_keyword_for_index,
)

__all__ = [
    "generate_key",
    "encrypt_document",
    "decrypt_document",
    "build_trapdoor",
    "encrypt_keyword_for_index",
]
