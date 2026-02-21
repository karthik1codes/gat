"""Document routes: upload, search, list, get content."""
import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models import User
from ..routes.auth import get_current_user_id
from ..sse_service import get_or_create_sse_client

router = APIRouter(prefix="/api/documents", tags=["documents"])


class SearchResponse(BaseModel):
    query: str
    document_ids: list[str]


@router.post("/upload")
async def upload_documents(
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    client = get_or_create_sse_client(user.id, user.sse_key_encrypted)[0]
    uploaded = []
    for f in files:
        if not f.filename or not f.filename.strip():
            continue
        content = await f.read()
        if not content:
            continue
        # Safe doc_id: strip extension, sanitize, ensure unique
        base = re.sub(r"[^\w\-.]", "_", f.filename.strip())[:100]
        if not base:
            base = "doc"
        doc_id = f"{base}_{uuid.uuid4().hex[:8]}"
        try:
            text = content.decode("utf-8")
        except Exception:
            text = content.decode("utf-8", errors="replace")
        client.upload_document(doc_id, content)
        uploaded.append({"id": doc_id, "filename": f.filename})
    return {"uploaded": uploaded, "count": len(uploaded)}


@router.get("/search", response_model=SearchResponse)
def search(
    q: str,
    user: User = Depends(get_current_user_id),
):
    if not q or not q.strip():
        return SearchResponse(query=q or "", document_ids=[])
    client = get_or_create_sse_client(user.id, user.sse_key_encrypted)[0]
    doc_ids = client.search(q.strip())
    return SearchResponse(query=q.strip(), document_ids=doc_ids)


@router.get("/")
def list_documents(
    user: User = Depends(get_current_user_id),
):
    client = get_or_create_sse_client(user.id, user.sse_key_encrypted)[0]
    ids = client._server.list_document_ids()
    return {"document_ids": ids}


@router.get("/{doc_id}/content")
def get_document_content(
    doc_id: str,
    user: User = Depends(get_current_user_id),
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
