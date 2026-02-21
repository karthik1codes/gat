"""Cryptographic primitives for Searchable Symmetric Encryption (SSE)."""

from .keys import (
    KeyBundle,
    derive_key_bundle,
    generate_master_key,
    key_identifier,
    constant_time_equals,
)
from .sse import (
    generate_key,
    encrypt_document,
    decrypt_document,
    build_trapdoor,
    encrypt_keyword_for_index,
    trapdoor_matches,
)
from .kdf import (
    VaultKeyBundle,
    derive_vault_keys,
    scrypt_derive,
    pbkdf2_derive,
    generate_salt,
)
from .vault import VaultManager, VaultState

__all__ = [
    "KeyBundle",
    "derive_key_bundle",
    "generate_master_key",
    "key_identifier",
    "constant_time_equals",
    "generate_key",
    "encrypt_document",
    "decrypt_document",
    "build_trapdoor",
    "encrypt_keyword_for_index",
    "trapdoor_matches",
    "VaultKeyBundle",
    "derive_vault_keys",
    "scrypt_derive",
    "pbkdf2_derive",
    "generate_salt",
    "VaultManager",
    "VaultState",
]
