"""Document routes: upload, search, list, get content."""
import json
import math
import re
import time
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
from ..sse_service import get_sse_client_for_vault
from ..services.vault_service import get_vault, get_storage_dir

# Filename encryption: server stores only encrypted form
from crypto.filename_encryption import encrypt_filename_structured

DOC_METADATA_FILENAME = "doc_metadata.json"


def _pdf_to_text(pdf_bytes: bytes) -> bytes:
    """Extract text from PDF bytes; return UTF-8 bytes for indexing. Raises ValueError on failure."""
    from io import BytesIO
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ValueError("PDF support not available. Install pypdf: pip install pypdf")
    if not pdf_bytes or len(pdf_bytes) < 100:
        raise ValueError("File is too small or empty to be a valid PDF.")
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception as e:
        raise ValueError(f"Could not read PDF: {e!s}")
    parts = []
    try:
        for page in reader.pages:
            t = page.extract_text()
            if t is not None and t.strip():
                parts.append(t)
    except Exception as e:
        raise ValueError(f"Could not extract text from PDF: {e!s}")
    text = "\n".join(parts).strip()
    if not text:
        raise ValueError(
            "No text could be extracted from this PDF (e.g. image-only or scanned). "
            "Use a PDF with selectable text, or convert with OCR."
        )
    return text.encode("utf-8", errors="replace")


def _doc_metadata_path(user_id: str, vault_id: str) -> Path:
    return get_storage_dir(user_id, vault_id) / DOC_METADATA_FILENAME


def _load_doc_metadata(user_id: str, vault_id: str) -> dict:
    """Return { \"files\": { doc_id: name_or_payload }, \"keyword_counter\": {} }."""
    p = _doc_metadata_path(user_id, vault_id)
    if not p.exists():
        return {"files": {}, "keyword_counter": {}}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"files": {}, "keyword_counter": {}}
    if "files" in raw and "keyword_counter" in raw:
        return raw
    # Legacy flat: whole thing is files
    return {"files": raw if isinstance(raw, dict) else {}, "keyword_counter": {}}


def _save_doc_metadata(user_id: str, vault_id: str, data: dict) -> None:
    p = _doc_metadata_path(user_id, vault_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def require_vault_unlocked(user: User = Depends(get_current_user_id)) -> User:
    """Require a vault to be selected and unlocked for document access."""
    if not user.current_vault_id:
        raise HTTPException(status_code=403, detail="Create or open a vault first to store documents.")
    vault = get_vault(user.id, user.current_vault_id)
    if not vault.is_unlocked():
        raise HTTPException(status_code=403, detail="Vault is locked. Unlock to access documents.")
    return user


def _get_sse_client(user: User):
    """Return SSE client for current vault (requires require_vault_unlocked)."""
    key = get_vault(user.id, user.current_vault_id).get_k_master_for_compat()
    if not key:
        raise HTTPException(status_code=403, detail="Vault keys not available.")
    return get_sse_client_for_vault(user.id, user.current_vault_id, key)


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


def _get_keyword_counter(user: User, vault_id: str) -> dict:
    """Load per-vault keyword counter for forward-private SSE (in vault doc_metadata)."""
    meta = _load_doc_metadata(user.id, vault_id)
    return meta.get("keyword_counter") or {}


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
    client = _get_sse_client(user)
    meta = _load_doc_metadata(user.id, user.current_vault_id)
    keyword_counter = meta.get("keyword_counter") or {}
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
        if ext == ".pdf":
            try:
                content = _pdf_to_text(content)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        base = re.sub(r"[^\w\-.]", "_", f.filename.strip())[:100]
        if not base:
            base = "doc"
        doc_id = f"{base}_{uuid.uuid4().hex[:8]}"
        documents_to_upload.append((doc_id, content))
        filenames.append((doc_id, f.filename))
    if not documents_to_upload:
        return {"uploaded": [], "count": 0}
    debug_files: list[dict] = [] if debug else []
    t0 = time.perf_counter()
    # Forward-private SSE by default: index keys depend on per-keyword counter
    client.upload_documents_forward_secure(
        keyword_counter, documents_to_upload, debug_collector=debug_files if debug else None
    )
    # Build substring (n-gram) and phonetic indexes for substring/fuzzy search
    client.upload_documents_substring_index(documents_to_upload, n=3)
    client.upload_documents_phonetic_index(documents_to_upload)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    db_user = db.query(User).filter(User.id == user.id).first()
    if db_user:
        db_user.last_upload_duration_ms = round(elapsed_ms, 2)
        db_user.last_upload_doc_count = len(documents_to_upload)
        db_user.last_uploaded_doc_ids_json = json.dumps([doc_id for doc_id, _ in documents_to_upload])
    db.commit()
    vault = get_vault(user.id, user.current_vault_id)
    keys = vault.get_keys() if vault.is_unlocked() else None
    meta["keyword_counter"] = keyword_counter
    for doc_id, fn in filenames:
        if keys and len(keys.k_filename_enc) == 32:
            meta.setdefault("files", {})[doc_id] = encrypt_filename_structured(fn, keys.k_filename_enc)
        else:
            meta.setdefault("files", {})[doc_id] = fn
    _save_doc_metadata(user.id, user.current_vault_id, meta)
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


def _record_search_metrics(db: Session, user_id: str, elapsed_ms: float, document_ids: list[str]) -> None:
    """Store last search latency and matched doc ids for real performance metrics."""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.last_search_latency_ms = round(elapsed_ms, 2)
        db_user.last_search_matched_doc_ids_json = json.dumps(document_ids)
        db.commit()


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
    db: Session = Depends(get_db),
):
    """
    Search. search_type: keyword, substring, fuzzy, ranked.
    For multi-keyword: set keywords=word1,word2 and mode=and|or (intersection or union).
    Pagination: skip, limit (default limit=100).
    """
    t0 = time.perf_counter()
    check_rate_limit(
        user.id, "search", RATE_LIMIT_SEARCH_PER_MINUTE, RATE_LIMIT_WINDOW_SECONDS
    )
    if len((q or "").strip()) > MAX_SEARCH_QUERY_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Search query too long (max {MAX_SEARCH_QUERY_LENGTH} characters).",
        )
    client = _get_sse_client(user)
    if pad_to > 0:
        client._known_doc_ids = set(client._server.list_document_ids())
    keyword_counter = _get_keyword_counter(user, user.current_vault_id)

    # Multi-keyword (AND/OR) when keywords param is set
    if keywords and keywords.strip():
        kw_list = [w.strip().lower() for w in keywords.split(",") if w.strip()]
        if len(kw_list) > MAX_KEYWORDS_MULTI:
            raise HTTPException(
                status_code=400,
                detail=f"Too many keywords (max {MAX_KEYWORDS_MULTI}).",
            )
        if not kw_list:
            _record_search_metrics(db, user.id, (time.perf_counter() - t0) * 1000, [])
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
        _record_search_metrics(db, user.id, (time.perf_counter() - t0) * 1000, doc_ids)
        return _search_response(keywords.strip(), doc_ids, total, client, kw_list, debug)

    if not q or not q.strip():
        _record_search_metrics(db, user.id, (time.perf_counter() - t0) * 1000, [])
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
    _record_search_metrics(db, user.id, (time.perf_counter() - t0) * 1000, doc_ids)
    return _search_response(q_clean, doc_ids, total, client, [q_clean], debug)


@router.get("/")
def list_documents(
    skip: int = 0,
    limit: int = 100,
    user: User = Depends(require_vault_unlocked),
):
    """List document IDs with pagination. Returns encrypted_filename_payload when set (client decrypts); else original_filename for legacy."""
    client = _get_sse_client(user)
    ids = client._server.list_document_ids()
    total = len(ids)
    ids = ids[skip : skip + limit]
    meta = _load_doc_metadata(user.id, user.current_vault_id)
    files = meta.get("files") or {}
    documents = []
    for doc_id in ids:
        val = files.get(doc_id)
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
    client = _get_sse_client(user)
    if not client._server.delete_document(doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    meta = _load_doc_metadata(user.id, user.current_vault_id)
    meta.setdefault("files", {}).pop(doc_id, None)
    _save_doc_metadata(user.id, user.current_vault_id, meta)
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
    client = _get_sse_client(user)
    if client._server.get_document(doc_id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    meta = _load_doc_metadata(user.id, user.current_vault_id)
    val = (meta.get("files") or {}).get(doc_id)
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
    client = _get_sse_client(user)
    plain = client.retrieve_and_decrypt(doc_id)
    if plain is None:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        text = plain.decode("utf-8")
        return PlainTextResponse(text)
    except Exception:
        from fastapi.responses import Response
        return Response(content=plain, media_type="application/octet-stream")
