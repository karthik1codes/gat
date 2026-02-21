"""Per-user SSE client/server; key storage in DB."""
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


def get_or_create_sse_client(user_id: str, sse_key_encrypted: Optional[bytes]) -> tuple[SSEClient, Optional[bytes]]:
    """
    Return (SSEClient for this user, new_encrypted_key_if_created).
    If sse_key_encrypted is None, generate new key, encrypt, return client and encrypted key to store.
    """
    storage_dir = USER_STORAGE_BASE / user_id
    storage_dir.mkdir(parents=True, exist_ok=True)
    server = SSEServer(storage_dir=storage_dir)

    if sse_key_encrypted:
        key = decrypt_sse_key(sse_key_encrypted)
        return SSEClient(master_key=key, server=server), None

    key = generate_key()
    client = SSEClient(master_key=key, server=server)
    return client, encrypt_sse_key(key)
