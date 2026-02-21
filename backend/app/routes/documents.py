"""Document routes: upload, search, list, get content."""
import json
import math
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..config import (
    ALLOWED_UPLOAD_EXTENSIONS,
    MAX_KEYWORDS_MULTI,
    MAX_SEARCH_QUERY_LENGTH,
    MAX_UPLOAD_BYTES,
    RATE_LIMIT_SEARCH_PER_MINUTE,
    RATE_LIMIT_UPLOAD_PER_MINUTE,
    RATE_LIMIT_WINDOW_SECONDS,
)
from ..database import get_db
from ..models import User
from ..rate_limit import check_rate_limit
from ..config import USER_STORAGE_BASE
from ..routes.auth import get_current_user_id
from ..sse_service import get_or_create_sse_client
from ..services.vault_service import get_vault

# Filename encryption: server stores only encrypted form
from crypto.filename_encryption import encrypt_filename_structured

DOC_METADATA_FILENAME = "doc_metadata.json"


def _doc_metadata_path(user_id: str) -> Path:
    return USER_STORAGE_BASE / user_id / DOC_METADATA_FILENAME


def _load_doc_metadata(user_id: str) -> dict:
    p = _doc_metadata_path(user_id)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_doc_metadata(user_id: str, data: dict) -> None:
    p = _doc_metadata_path(user_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def require_vault_unlocked(user: User = Depends(get_current_user_id)) -> User:
    """Require vault to be created and unlocked for document access."""
    if user.vault_salt is None:
        raise HTTPException(status_code=403, detail="Create a vault first to store documents.")
    vault = get_vault(user.id)
    if not vault.is_unlocked():
        raise HTTPException(status_code=403, detail="Vault is locked. Unlock to access documents.")
    return user


router = APIRouter(prefix="/api/documents", tags=["documents"])


class SearchResponse(BaseModel):
    query: str
    document_ids: list[str]
    total: int | None = None  # total count before pagination


class SearchDebugInfo(BaseModel):
    search_token: str
    matched_encrypted_doc_ids: list[str]
    encryption_algorithm: str = "AES-256-GCM"
    token_algorithm: str = "HMAC-SHA256"
    index_lookup_performed: bool = True
    result_count: int


def _get_keyword_counter(user: User) -> dict:
    """Load per-user keyword counter for forward-private SSE (persisted in DB)."""
    if not user.keyword_counter_json:
        return {}
    try:
        return json.loads(user.keyword_counter_json)
    except (json.JSONDecodeError, TypeError):
        return {}


def _rank_by_tfidf(client, query: str, doc_ids: list, top_k: int) -> list:
    """Rank doc_ids by TF-IDF for query (client-side scores); return top_k."""
    w = query.strip().lower()
    if not w or not doc_ids:
        return []
    N = len(client._server.list_document_ids()) or 1
    df = len(doc_ids)
    idf = math.log((N + 1) / (df + 1)) + 1.0
    scores = []
    for doc_id in doc_ids:
        plain = client.retrieve_and_decrypt(doc_id)
        if plain is None:
            continue
        text = plain.decode("utf-8", errors="replace").lower()
        terms = text.split()
        if not terms:
            scores.append((doc_id, 0.0))
            continue
        tf = sum(1 for t in terms if t == w) / len(terms)
        scores.append((doc_id, tf * idf))
    scores.sort(key=lambda x: -x[1])
    return [doc_id for doc_id, _ in scores[:top_k]]


@router.post("/upload")
async def upload_documents(
    files: list[UploadFile] = File(...),
    debug: bool = Query(False, description="Include safe crypto trace metadata (Judge Mode)"),
    user: User = Depends(require_vault_unlocked),
    db: Session = Depends(get_db),
):
    check_rate_limit(
        user.id, "upload", RATE_LIMIT_UPLOAD_PER_MINUTE, RATE_LIMIT_WINDOW_SECONDS
    )
    client, _ = get_or_create_sse_client(user.id, user.sse_key_encrypted)
    keyword_counter = _get_keyword_counter(user)
    documents_to_upload = []
    filenames = []
    for f in files:
        if not f.filename or not f.filename.strip():
            continue
        content = await f.read()
        if not content:
            continue
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Upload failed: file too large (max {MAX_UPLOAD_BYTES // (1024*1024)} MiB).",
            )
        ext = Path(f.filename).suffix.lower()
        if ext and ext not in ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Upload failed: file type not allowed. Allowed: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}.",
            )
        base = re.sub(r"[^\w\-.]", "_", f.filename.strip())[:100]
        if not base:
            base = "doc"
        doc_id = f"{base}_{uuid.uuid4().hex[:8]}"
        documents_to_upload.append((doc_id, content))
        filenames.append((doc_id, f.filename))
    if not documents_to_upload:
        return {"uploaded": [], "count": 0}
    debug_files: list[dict] = [] if debug else []
    # Forward-private SSE by default: index keys depend on per-keyword counter
    client.upload_documents_forward_secure(
        keyword_counter, documents_to_upload, debug_collector=debug_files if debug else None
    )
    # Build substring (n-gram) and phonetic indexes for substring/fuzzy search
    client.upload_documents_substring_index(documents_to_upload, n=3)
    client.upload_documents_phonetic_index(documents_to_upload)
    user.keyword_counter_json = json.dumps(keyword_counter)
    db.commit()
    vault = get_vault(user.id)
    keys = vault.get_keys() if vault.is_unlocked() else None
    meta = _load_doc_metadata(user.id)
    for doc_id, fn in filenames:
        if keys and len(keys.k_filename_enc) == 32:
            meta[doc_id] = encrypt_filename_structured(fn, keys.k_filename_enc)
        else:
            meta[doc_id] = fn  # fallback: store plaintext only if vault keys unavailable (should not happen when unlocked)
    _save_doc_metadata(user.id, meta)
    uploaded = [
        {"id": doc_id, "filename": fn, "encrypted_path": f"vault/documents/{doc_id}"}
        for doc_id, fn in filenames
    ]
    out: dict = {"uploaded": uploaded, "count": len(uploaded)}
    if debug and debug_files:
        out["debug"] = {"files": debug_files}
    return out


def _single_keyword_doc_ids(client, keyword_counter: dict, q: str, pad_to: int):
    """Return doc_id set for one keyword (forward_secure + legacy)."""
    doc_ids_set = set()
    if keyword_counter:
        doc_ids_set.update(
            client.search_forward_secure(keyword_counter, q, pad_to=pad_to)
        )
    doc_ids_set.update(client.search(q, pad_to=pad_to))
    return doc_ids_set


def _search_response(
    query: str,
    document_ids: list[str],
    total: int | None,
    client,
    keywords_for_token: list[str],
    debug: bool,
):
    """Build search response with optional debug metadata (no secrets)."""
    out: dict = {
        "query": query,
        "document_ids": document_ids,
        "total": total,
    }
    if debug and client is not None:
        search_token = ""
        if keywords_for_token:
            search_token = client.get_trapdoor_hex(keywords_for_token[0])
        out["debug"] = SearchDebugInfo(
            search_token=search_token,
            matched_encrypted_doc_ids=list(document_ids),
            encryption_algorithm="AES-256-GCM",
            token_algorithm="HMAC-SHA256",
            index_lookup_performed=True,
            result_count=len(document_ids),
        ).model_dump()
    return out


@router.get("/search")
def search(
    q: str,
    pad_to: int = 0,
    search_type: str = "keyword",
    top_k: int = 20,
    keywords: str | None = None,
    mode: str = "or",
    skip: int = 0,
    limit: int = 100,
    debug: bool = Query(False, description="Include safe crypto trace metadata (Judge Mode)"),
    user: User = Depends(require_vault_unlocked),
):
    """
    Search. search_type: keyword, substring, fuzzy, ranked.
    For multi-keyword: set keywords=word1,word2 and mode=and|or (intersection or union).
    Pagination: skip, limit (default limit=100).
    """
    check_rate_limit(
        user.id, "search", RATE_LIMIT_SEARCH_PER_MINUTE, RATE_LIMIT_WINDOW_SECONDS
    )
    if len((q or "").strip()) > MAX_SEARCH_QUERY_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Search query too long (max {MAX_SEARCH_QUERY_LENGTH} characters).",
        )
    client = get_or_create_sse_client(user.id, user.sse_key_encrypted)[0]
    if pad_to > 0:
        client._known_doc_ids = set(client._server.list_document_ids())
    keyword_counter = _get_keyword_counter(user)

    # Multi-keyword (AND/OR) when keywords param is set
    if keywords and keywords.strip():
        kw_list = [w.strip().lower() for w in keywords.split(",") if w.strip()]
        if len(kw_list) > MAX_KEYWORDS_MULTI:
            raise HTTPException(
                status_code=400,
                detail=f"Too many keywords (max {MAX_KEYWORDS_MULTI}).",
            )
        if not kw_list:
            return _search_response(keywords.strip(), [], None, client, kw_list, debug)
        sets = []
        for w in kw_list:
            sets.append(_single_keyword_doc_ids(client, keyword_counter, w, pad_to))
        if mode.lower() == "and":
            doc_ids = list(sets[0].intersection(*sets[1:])) if len(sets) > 1 else list(sets[0])
        else:
            doc_ids = list(sets[0].union(*sets[1:]) if len(sets) > 1 else sets[0])
        total = len(doc_ids)
        doc_ids = doc_ids[skip : skip + limit]
        return _search_response(keywords.strip(), doc_ids, total, client, kw_list, debug)

    if not q or not q.strip():
        return _search_response(q or "", [], None, client, [], debug)
    q_clean = q.strip()
    if search_type == "substring":
        doc_ids = client.search_substring(q_clean, n=3, pad_to=pad_to)
    elif search_type == "fuzzy":
        doc_ids = client.search_fuzzy(q_clean, max_edit_distance=2)
    elif search_type == "ranked":
        doc_ids_set = set()
        if keyword_counter:
            doc_ids_set.update(client.search_forward_secure(keyword_counter, q_clean))
        doc_ids_set.update(client.search(q_clean))
        doc_ids = _rank_by_tfidf(client, q_clean, list(doc_ids_set), max(1, min(top_k, 100)))
    else:
        doc_ids = list(_single_keyword_doc_ids(client, keyword_counter, q_clean, pad_to))
    total = len(doc_ids)
    doc_ids = doc_ids[skip : skip + limit]
    return _search_response(q_clean, doc_ids, total, client, [q_clean], debug)


@router.get("/")
def list_documents(
    skip: int = 0,
    limit: int = 100,
    user: User = Depends(require_vault_unlocked),
):
    """List document IDs with pagination. Returns encrypted_filename_payload when set (client decrypts); else original_filename for legacy."""
    client = get_or_create_sse_client(user.id, user.sse_key_encrypted)[0]
    ids = client._server.list_document_ids()
    total = len(ids)
    ids = ids[skip : skip + limit]
    meta = _load_doc_metadata(user.id)
    documents = []
    for doc_id in ids:
        val = meta.get(doc_id)
        if isinstance(val, dict) and "encrypted_filename" in val:
            documents.append({"id": doc_id, "encrypted_filename_payload": val})
        else:
            documents.append({"id": doc_id, "original_filename": val if isinstance(val, str) else doc_id})
    return {"document_ids": ids, "total": total, "documents": documents}


@router.delete("/{doc_id}")
def delete_document(
    doc_id: str,
    user: User = Depends(require_vault_unlocked),
):
    """Remove a document and its index entries."""
    client = get_or_create_sse_client(user.id, user.sse_key_encrypted)[0]
    if not client._server.delete_document(doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    meta = _load_doc_metadata(user.id)
    meta.pop(doc_id, None)
    _save_doc_metadata(user.id, meta)
    return {"deleted": doc_id}


@router.get("/{doc_id}/encrypted-path")
def get_encrypted_path(
    doc_id: str,
    user: User = Depends(require_vault_unlocked),
):
    """
    Return the encrypted storage path for a document (for "Locate Encrypted File").
    If filename is stored encrypted, returns encrypted_filename_payload (client decrypts); else original_filename (legacy).
    """
    client = get_or_create_sse_client(user.id, user.sse_key_encrypted)[0]
    if client._server.get_document(doc_id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    meta = _load_doc_metadata(user.id)
    val = meta.get(doc_id)
    encrypted_path = f"vault/documents/{doc_id}"
    if isinstance(val, dict) and "encrypted_filename" in val:
        return {"doc_id": doc_id, "encrypted_path": encrypted_path, "encrypted_filename_payload": val}
    return {
        "doc_id": doc_id,
        "encrypted_path": encrypted_path,
        "original_filename": val if isinstance(val, str) else doc_id,
    }


@router.get("/{doc_id}/content")
def get_document_content(
    doc_id: str,
    user: User = Depends(require_vault_unlocked),
):
    client = get_or_create_sse_client(user.id, user.sse_key_encrypted)[0]
    plain = client.retrieve_and_decrypt(doc_id)
    if plain is None:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        text = plain.decode("utf-8")
        return PlainTextResponse(text)
    except Exception:
        from fastapi.responses import Response
        return Response(content=plain, media_type="application/octet-stream")
