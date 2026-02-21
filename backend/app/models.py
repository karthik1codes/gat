"""SQLAlchemy models for users and per-user SSE key storage."""
from sqlalchemy import Column, String, LargeBinary, DateTime
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(String(64), primary_key=True)  # uuid
    google_id = Column(String(128), unique=True, nullable=False, index=True)
    email = Column(String(256), nullable=False)
    name = Column(String(256), nullable=True)
    picture = Column(String(512), nullable=True)
    sse_key_encrypted = Column(LargeBinary, nullable=True)  # encrypted with server secret
    keyword_counter_json = Column(String, nullable=True)  # JSON dict for forward-private SSE: keyword -> count
    vault_salt = Column(LargeBinary, nullable=True)  # salt for vault KDF (not secret; used with password)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
