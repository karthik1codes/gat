"""Per-user / per-vault SSE client/server; key from vault or DB."""
import sys
from pathlib import Path
from typing import Optional

# Project root on path for crypto, client, server
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto import generate_key
from client import SSEClient
from server import SSEServer

from .config import USER_STORAGE_BASE
from .auth_utils import encrypt_sse_key, decrypt_sse_key
from .services.index_service import migrate_json_to_sqlite
from .services.vault_service import get_storage_dir


def get_or_create_sse_client(user_id: str, sse_key_encrypted: Optional[bytes]) -> tuple[SSEClient, Optional[bytes]]:
    """
    Legacy: (SSEClient for this user, new_encrypted_key_if_created).
    Uses storage_dir = USER_STORAGE_BASE / user_id. Prefer get_sse_client_for_vault when using multi-vault.
    """
    storage_dir = USER_STORAGE_BASE / user_id
    storage_dir.mkdir(parents=True, exist_ok=True)
    migrate_json_to_sqlite(storage_dir)
    server = SSEServer(storage_dir=storage_dir, use_sqlite_index=True)

    if sse_key_encrypted:
        key = decrypt_sse_key(sse_key_encrypted)
        return SSEClient(master_key=key, server=server), None

    key = generate_key()
    client = SSEClient(master_key=key, server=server)
    return client, encrypt_sse_key(key)


def get_sse_client_for_vault(user_id: str, vault_id: str, master_key: bytes) -> SSEClient:
    """
    Return SSEClient for the given vault using vault-scoped storage and the vault's master key.
    Caller must ensure vault is unlocked and pass get_vault(...).get_k_master_for_compat().
    """
    storage_dir = get_storage_dir(user_id, vault_id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    migrate_json_to_sqlite(storage_dir)
    server = SSEServer(storage_dir=storage_dir, use_sqlite_index=True)
    return SSEClient(master_key=master_key, server=server)
