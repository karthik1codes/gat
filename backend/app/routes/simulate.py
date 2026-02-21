"""
Attack simulation: returns what an honest-but-curious server sees.
Exposes only safe metadata (encrypted identifiers, token, sizes). No plaintext, no keys.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import APIRouter, Depends, Query

from ..routes.auth import get_current_user_id
from ..routes.documents import require_vault_unlocked
from ..models import User
from ..sse_service import get_or_create_sse_client

router = APIRouter(prefix="/api/simulate", tags=["simulate"])


def simulate_server_perspective(
    client,
    query: str,
    pad_to: int = 0,
) -> dict:
    """
    Internal: build the view an honest-but-curious server has for a search.
    Returns only: encrypted_filename (doc IDs), search_token, matched_doc_ids,
    ciphertext_size (per doc if available), index_size.
    Does NOT return: plaintext content, secret key, derived keys, decrypted data.
    """
    token_hex = client.get_trapdoor_hex(query.strip().lower() if query else "")
    doc_ids = client._server.search(
        bytes.fromhex(token_hex) if token_hex else b"",
        pad_to=pad_to,
    )
    storage_dir = client._server.storage_dir
    index_path = storage_dir / "index.db"
    if not index_path.exists():
        index_path = storage_dir / "index.json"
    index_size = index_path.stat().st_size if index_path.exists() else 0
    ciphertext_sizes = []
    for doc_id in doc_ids[:10]:
        ct = client._server.get_document(doc_id)
        if ct is not None:
            ciphertext_sizes.append(len(ct))
    return {
        "encrypted_filename": "N/A (server sees doc IDs only)",
        "search_token": token_hex,
        "matched_doc_ids": doc_ids,
        "ciphertext_size": sum(ciphertext_sizes) if ciphertext_sizes else 0,
        "ciphertext_sizes_sample": ciphertext_sizes[:5],
        "index_size": index_size,
        "result_count": len(doc_ids),
    }


@router.get("/server-view")
def simulate_server_view(
    q: str = Query("", description="Search keyword to simulate"),
    pad_to: int = Query(0, ge=0),
    user: User = Depends(require_vault_unlocked),
):
    """
    Returns what an honest-but-curious server sees for a search.
    Safe metadata only: encrypted_filename (description), search_token,
    matched_encrypted_doc_ids, ciphertext_size, index_size.
    Never returns: plaintext content, secret key, derived keys, raw decrypted data.
    """
    client = get_or_create_sse_client(user.id, user.sse_key_encrypted)[0]
    data = simulate_server_perspective(client, q, pad_to=pad_to)
    return {
        "encrypted_filename": data["encrypted_filename"],
        "search_token": data["search_token"],
        "matched_doc_ids": data["matched_doc_ids"],
        "ciphertext_size": data["ciphertext_size"],
        "index_size": data["index_size"],
    }
