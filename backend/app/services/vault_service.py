"""
Per-user vault management: unlock/lock, in-memory keys only, auto-lock, stats.
Keys never stored in plaintext; cleared on lock.
"""

import sys
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto.vault import VaultManager, VaultState
from crypto.kdf import VaultKeyBundle
from server import SSEServer

from ..config import USER_STORAGE_BASE

# Per-user vault: user_id -> VaultManager (in-memory only)
_vaults: Dict[str, VaultManager] = {}
_default_inactivity_timeout = 300.0  # 5 minutes


def get_vault(user_id: str, inactivity_timeout: Optional[float] = None) -> VaultManager:
    """Get or create VaultManager for user. Keys only in memory."""
    if user_id not in _vaults:
        timeout = inactivity_timeout if inactivity_timeout is not None else _default_inactivity_timeout
        _vaults[user_id] = VaultManager(inactivity_timeout_seconds=timeout)
    return _vaults[user_id]


def check_inactivity_and_lock(user_id: str) -> bool:
    """If vault inactive past timeout, lock it. Returns True if locked."""
    if user_id not in _vaults:
        return False
    return _vaults[user_id].check_inactivity_and_lock()


def lock_vault(user_id: str) -> None:
    """Manual lock; clears key material for user."""
    if user_id in _vaults:
        _vaults[user_id].lock_vault()


def get_vault_stats(user_id: str) -> dict:
    """
    Metrics for dashboard: total encrypted files, total size, index size,
    algorithm names, KDF info, last unlock time.
    """
    storage_dir = USER_STORAGE_BASE / user_id
    docs_path = storage_dir / "documents"
    index_path = storage_dir / "index.db"
    index_json = storage_dir / "index.json"
    total_files = 0
    total_size = 0
    if docs_path.exists():
        for f in docs_path.iterdir():
            if f.is_file():
                total_files += 1
                total_size += f.stat().st_size
    index_size = 0
    if index_path.exists():
        index_size = index_path.stat().st_size
    elif index_json.exists():
        index_size = index_json.stat().st_size
    vault = get_vault(user_id)
    last_activity = vault.get_last_activity_time() if vault.is_unlocked() else None
    return {
        "total_encrypted_files": total_files,
        "total_encrypted_size_bytes": total_size,
        "index_size_bytes": index_size,
        "encryption_algorithm": "AES-256-GCM",
        "kdf_algorithm": "scrypt",
        "kdf_iterations_equivalent": 32768,
        "last_unlock_timestamp": last_activity,
        "vault_state": vault.get_state().value,
    }
