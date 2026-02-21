"""FastAPI application: CORS, auth and document routes."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load .env before any app config is read
try:
    from dotenv import load_dotenv
    load_dotenv(str(ROOT / "backend" / ".env"))
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from sqlalchemy import text

from .database import engine, Base, get_db
from .routes import auth, documents, vault

# Create tables
Base.metadata.create_all(bind=engine)

# Ensure User.keyword_counter_json exists (forward-private SSE)
with engine.connect() as conn:
    r = conn.execute(text("PRAGMA table_info(users)"))
    cols = [row[1] for row in r]
    if "keyword_counter_json" not in cols:
        conn.execute(text("ALTER TABLE users ADD COLUMN keyword_counter_json VARCHAR"))
        conn.commit()
    if "vault_salt" not in cols:
        conn.execute(text("ALTER TABLE users ADD COLUMN vault_salt BLOB"))
        conn.commit()

app = FastAPI(
    title="Secured String Matching API",
    description="Searchable Encryption: upload, search, and retrieve encrypted documents",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(vault.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/docs/threat-model", response_class=PlainTextResponse)
def threat_model():
    """Return THREAT_MODEL.md for privacy documentation (no auth required)."""
    path = ROOT / "THREAT_MODEL.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return PlainTextResponse(path.read_text(encoding="utf-8"))


@app.get("/api/security-info")
def security_info():
    """
    Return safe cryptographic metadata for Judge Mode / transparency.
    No auth required. Exposes only algorithm names and leakage profile (no secrets).
    """
    return {
        "encryption": "AES-256-GCM",
        "token_generation": "HMAC-SHA256",
        "key_size_bits": 256,
        "leakage_profile": {
            "search_pattern": True,
            "access_pattern": True,
            "content_leakage": False,
        },
    }
