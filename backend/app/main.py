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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base, get_db
from .routes import auth, documents

# Create tables
Base.metadata.create_all(bind=engine)

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


@app.get("/api/health")
def health():
    return {"status": "ok"}
