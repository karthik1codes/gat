"""SQLAlchemy models for users and per-user SSE key storage."""
from sqlalchemy import Column, String, LargeBinary, DateTime, Integer, Float
from sqlalchemy.sql import func
from .database import Base


class Vault(Base):
    __tablename__ = "vaults"
    id = Column(String(64), primary_key=True)  # uuid
    user_id = Column(String(64), nullable=False, index=True)  # owner (users.id)
    name = Column(String(256), nullable=False)
    salt = Column(LargeBinary, nullable=False)
    verifier = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    id = Column(String(64), primary_key=True)  # uuid
    google_id = Column(String(128), unique=True, nullable=False, index=True)
    email = Column(String(256), nullable=False)
    name = Column(String(256), nullable=True)
    picture = Column(String(512), nullable=True)
    sse_key_encrypted = Column(LargeBinary, nullable=True)  # encrypted with server secret
    keyword_counter_json = Column(String, nullable=True)  # JSON dict for forward-private SSE: keyword -> count (legacy)
    vault_salt = Column(LargeBinary, nullable=True)  # legacy single-vault; migrated to Vault table
    vault_verifier = Column(LargeBinary, nullable=True)  # legacy
    current_vault_id = Column(String(64), nullable=True)  # which vault is active (vaults.id)
    # Real performance metrics (from user uploads and searches)
    last_upload_duration_ms = Column(Float, nullable=True)
    last_upload_doc_count = Column(Integer, nullable=True)
    last_search_latency_ms = Column(Float, nullable=True)
    last_uploaded_doc_ids_json = Column(String, nullable=True)  # JSON array of doc_ids from last upload
    last_search_matched_doc_ids_json = Column(String, nullable=True)  # JSON array of doc_ids from last search
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
