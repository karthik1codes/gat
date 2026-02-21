"""
Real performance metrics: from user's uploaded documents and search activity.
Per-document breakdown; index size read from disk each time. No synthetic data.
"""

import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..services.vault_service import get_vault_stats
from ..routes.documents import require_vault_unlocked, _get_sse_client

router = APIRouter(prefix="/api/performance", tags=["performance"])


def _parse_json_ids(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        out = json.loads(raw)
        return list(out) if isinstance(out, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


@router.get("/real")
def real_performance_metrics(
    user: User = Depends(require_vault_unlocked),
    db: Session = Depends(get_db),
):
    """
    Return real performance metrics per document and totals.
    Index size is read from disk on every request. Per-doc: index share, encryption (from last upload), matched in last search.
    """
    # Always read index size from disk (no caching)
    stats = get_vault_stats(user.id, user.current_vault_id)
    document_count = stats.get("total_encrypted_files", 0) or 0
    index_size_bytes = stats.get("index_size_bytes", 0) or 0
    index_size_kb = round(index_size_bytes / 1024, 2)

    db_user = db.query(User).filter(User.id == user.id).first()
    last_upload_ms = db_user.last_upload_duration_ms if db_user else None
    last_upload_count = db_user.last_upload_doc_count if db_user else None
    last_search_ms = db_user.last_search_latency_ms if db_user else None
    last_uploaded_ids = _parse_json_ids(db_user.last_uploaded_doc_ids_json) if db_user else []
    last_matched_ids = _parse_json_ids(db_user.last_search_matched_doc_ids_json) if db_user else []

    doc_ids = []
    try:
        client = _get_sse_client(user)
        doc_ids = list(client._server.list_document_ids())
    except Exception:
        pass

    # Per-document: index share (total / n), encryption approx (from last upload batch), matched in last search
    n = len(doc_ids) or 1
    index_share_kb = round(index_size_bytes / 1024 / n, 2) if doc_ids else 0
    encryption_per_doc_ms = round(last_upload_ms / last_upload_count, 2) if (last_upload_ms is not None and last_upload_count) else None

    documents = []
    for doc_id in doc_ids:
        in_last_upload = doc_id in last_uploaded_ids
        documents.append({
            "id": doc_id,
            "index_share_kb": index_share_kb,
            "encryption_ms": encryption_per_doc_ms if in_last_upload else None,
            "matched_in_last_search": doc_id in last_matched_ids,
        })

    return {
        "document_count": document_count,
        "index_size_bytes": index_size_bytes,
        "index_size_kb": index_size_kb,
        "last_upload_duration_ms": last_upload_ms,
        "last_upload_doc_count": last_upload_count,
        "last_search_latency_ms": last_search_ms,
        "has_search_result": last_search_ms is not None,
        "documents": documents,
    }
