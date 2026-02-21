"""
Vault state and key lifecycle (Cryptomator-inspired).

- LOCKED: no decryption possible; no keys in memory.
- UNLOCKED: keys in memory only; auto-lock after inactivity or manual lock.
- Keys never stored in plaintext on server; overwritten on lock.
"""

import hashlib
import os
import time
from enum import Enum
from typing import Optional, Union, Tuple

from .kdf import (
    VaultKeyBundle,
    derive_vault_keys,
    derive_vault_keys_from_password,
    generate_salt,
)


class VaultState(str, Enum):
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"


def _secure_zero(b: bytearray) -> None:
    """Overwrite buffer with zeros to reduce exposure of key material."""
    for i in range(len(b)):
        b[i] = 0


class VaultManager:
    """
    Manages vault state and in-memory keys only.
    Keys are derived from password on unlock and cleared on lock.
    """

    def __init__(self, inactivity_timeout_seconds: Optional[float] = 300.0):
        self._state = VaultState.LOCKED
        self._keys: Optional[VaultKeyBundle] = None
        self._k_master_buf: Optional[bytearray] = None
        self._salt: Optional[bytes] = None
        self._inactivity_timeout = inactivity_timeout_seconds
        self._last_activity: float = 0.0

    def is_unlocked(self) -> bool:
        return self._state == VaultState.UNLOCKED and self._keys is not None

    def get_state(self) -> VaultState:
        return self._state

    def get_keys(self) -> Optional[VaultKeyBundle]:
        """Return key bundle only when unlocked. Do not persist the returned reference."""
        if not self.is_unlocked():
            return None
        self._last_activity = time.monotonic()
        return self._keys

    def get_k_master_for_compat(self) -> Optional[bytes]:
        """
        Return 32-byte key compatible with existing derive_key_bundle (HKDF from keys.py).
        Used to keep search/forward-privacy working with existing client logic.
        """
        if not self._k_master_buf:
            return None
        self._last_activity = time.monotonic()
        return bytes(self._k_master_buf)

    def load_vault(
        self,
        password: bytes,
        salt: Optional[bytes] = None,
        use_scrypt: bool = True,
        stored_verifier: Optional[bytes] = None,
    ) -> Union[bytes, Tuple[bytes, bytes]]:
        """
        Unlock vault with password. Derives keys; stores in memory only.
        If salt is None, generates a new salt (caller must persist for next unlock).
        If stored_verifier is set, verifies that password-derived K_master matches (else raises ValueError).
        Returns salt when re-unlocking; returns (salt, verifier) when creating (salt was None).
        """
        created = False
        if salt is None:
            salt = generate_salt()
            created = True
        if len(salt) < 16:
            raise ValueError("Salt must be at least 16 bytes")
        self._salt = salt
        k_master, bundle = derive_vault_keys_from_password(password, salt, use_scrypt=use_scrypt)
        verifier = hashlib.sha256(k_master).digest()
        if stored_verifier is not None and verifier != stored_verifier:
            raise ValueError("Invalid password")
        self._store_keys(k_master, bundle)
        self._state = VaultState.UNLOCKED
        self._last_activity = time.monotonic()
        if created:
            return (salt, verifier)
        return salt

    def unlock_with_master_key(self, k_master: bytes) -> None:
        """
        Unlock using an existing K_master (e.g. after key retrieval from server).
        Used for backward compatibility when vault is unlocked with stored encrypted key.
        """
        if len(k_master) < 32:
            raise ValueError("K_master must be at least 32 bytes")
        bundle = derive_vault_keys(k_master)
        self._store_keys(k_master, bundle)
        self._state = VaultState.UNLOCKED
        self._last_activity = time.monotonic()
        self._salt = None

    def _store_keys(self, k_master: bytes, bundle: VaultKeyBundle) -> None:
        """Store keys in mutable buffers so we can zero them on lock."""
        self._k_master_buf = bytearray(k_master)
        self._keys = bundle

    def lock_vault(self) -> None:
        """Clear all key material from memory and set state to LOCKED."""
        if self._k_master_buf is not None:
            _secure_zero(self._k_master_buf)
            self._k_master_buf = None
        self._keys = None
        self._state = VaultState.LOCKED
        # Salt is not secret; can keep for re-unlock
        # self._salt = None  # optional: clear if not persisting

    def check_inactivity_and_lock(self) -> bool:
        """
        If inactivity timeout exceeded, lock vault. Returns True if locked.
        Call periodically from API or background task.
        """
        if not self.is_unlocked() or self._inactivity_timeout is None or self._inactivity_timeout <= 0:
            return False
        if time.monotonic() - self._last_activity >= self._inactivity_timeout:
            self.lock_vault()
            return True
        return False

    def get_salt(self) -> Optional[bytes]:
        """Return stored salt (for persistence). Not secret."""
        return self._salt

    def get_last_activity_time(self) -> float:
        """Monotonic time of last activity (for stats)."""
        return self._last_activity
