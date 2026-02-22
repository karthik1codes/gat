"""
Security tests: vault lock/unlock, key derivation, encryption roundtrip,
tampered ciphertext/index detection. No demo code; cryptographically sound checks.
"""

import os
import pytest

# Ensure project root on path
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto.kdf import (
    generate_salt,
    scrypt_derive,
    pbkdf2_derive,
    derive_vault_keys,
    derive_vault_keys_from_password,
    VaultKeyBundle,
)
from crypto.vault import VaultManager, VaultState
from crypto.file_encryption import encrypt_file_payload, decrypt_file_payload
from crypto.filename_encryption import encrypt_filename, decrypt_filename
from crypto.index_protection import (
    sign_index_entry,
    verify_index_entry,
    sign_index_block,
    verify_index_block,
)


def test_scrypt_derive_consistent():
    password = b"test_password_123"
    salt = generate_salt()
    k1 = scrypt_derive(password, salt)
    k2 = scrypt_derive(password, salt)
    assert k1 == k2
    assert len(k1) == 32


def test_scrypt_derive_different_salt():
    password = b"test_password_123"
    k1 = scrypt_derive(password, generate_salt())
    k2 = scrypt_derive(password, generate_salt())
    assert k1 != k2


def test_pbkdf2_derive_consistent():
    password = b"test_password_123"
    salt = generate_salt()
    k1 = pbkdf2_derive(password, salt, iterations=200_000)
    k2 = pbkdf2_derive(password, salt, iterations=200_000)
    assert k1 == k2
    assert len(k1) == 32


def test_derive_vault_keys_deterministic():
    k_master = os.urandom(32)
    b1 = derive_vault_keys(k_master)
    b2 = derive_vault_keys(k_master)
    assert b1.k_file_enc == b2.k_file_enc
    assert b1.k_search != b1.k_index_mac  # domain separation


def test_vault_lock_unlock():
    vm = VaultManager(inactivity_timeout_seconds=60)
    assert vm.get_state() == VaultState.LOCKED
    assert not vm.is_unlocked()
    result = vm.load_vault(b"password123", salt=None)
    # When creating (salt=None), returns (salt, verifier); when re-unlocking, returns salt
    salt = result[0] if isinstance(result, tuple) else result
    assert len(salt) >= 16
    assert vm.is_unlocked()
    assert vm.get_state() == VaultState.UNLOCKED
    assert vm.get_keys() is not None
    vm.lock_vault()
    assert not vm.is_unlocked()
    assert vm.get_keys() is None


def test_vault_unlock_with_salt():
    salt = generate_salt()
    vm1 = VaultManager()
    vm1.load_vault(b"secret", salt=salt)
    keys1 = vm1.get_keys()
    vm1.lock_vault()
    vm2 = VaultManager()
    vm2.load_vault(b"secret", salt=salt)
    keys2 = vm2.get_keys()
    assert keys1 is not None and keys2 is not None
    assert keys2.k_file_enc == keys1.k_file_enc  # same password+salt => same keys


def test_file_encryption_roundtrip():
    key = os.urandom(32)
    plain = b"secret document content"
    blob = encrypt_file_payload(plain, key)
    assert len(blob) > len(plain)
    dec = decrypt_file_payload(blob, key)
    assert dec == plain


def test_file_encryption_tampered_detection():
    key = os.urandom(32)
    plain = b"secret"
    blob = encrypt_file_payload(plain, key)
    blob_tampered = bytearray(blob)
    blob_tampered[-1] ^= 1
    with pytest.raises(Exception):  # verification failed
        decrypt_file_payload(bytes(blob_tampered), key)


def test_filename_encryption_roundtrip():
    key = os.urandom(32)
    name = "invoice_2024.pdf"
    enc = encrypt_filename(name, key)
    assert isinstance(enc, str)
    dec = decrypt_filename(enc, key)
    assert dec == name


def test_filename_encryption_tampered():
    key = os.urandom(32)
    enc = encrypt_filename("test.txt", key)
    enc_bad = enc[:-1] + ("A" if enc[-1] != "A" else "B")
    with pytest.raises(Exception):
        decrypt_filename(enc_bad, key)


def test_index_entry_sign_verify():
    key = os.urandom(32)
    trapdoor_hex = "a" * 64
    doc_ids = ["doc1", "doc2"]
    mac = sign_index_entry(trapdoor_hex, doc_ids, key)
    assert verify_index_entry(trapdoor_hex, doc_ids, mac, key)
    assert not verify_index_entry(trapdoor_hex, ["doc1"], mac, key)
    assert not verify_index_entry(trapdoor_hex, doc_ids, bytes(32), key)


def test_index_block_sign_verify():
    key = os.urandom(32)
    entries = {"key1": ["a", "b"], "key2": ["c"]}
    mac = sign_index_block(entries, key)
    assert verify_index_block(entries, mac, key)
    entries_tampered = {"key1": ["a", "b", "x"], "key2": ["c"]}
    assert not verify_index_block(entries_tampered, mac, key)
