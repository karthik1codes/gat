"""App configuration from environment."""
import os
from pathlib import Path

# Project root (gat/) for crypto, client, server
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env from backend directory
try:
    from dotenv import load_dotenv
    load_dotenv(str(ROOT_DIR / "backend" / ".env"))
except ImportError:
    pass

# Google OAuth
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
if not GOOGLE_CLIENT_ID and os.environ.get("GAT_GOOGLE_CLIENT_ID"):
    GOOGLE_CLIENT_ID = os.environ["GAT_GOOGLE_CLIENT_ID"]

# Encrypt per-user SSE keys at rest (32 bytes hex = 64 chars)
SERVER_SECRET = os.environ.get("GAT_SERVER_SECRET", "dev-secret-change-in-production-32b")
if len(SERVER_SECRET) < 32:
    SERVER_SECRET = (SERVER_SECRET + "0" * 32)[:32]

# JWT
JWT_SECRET = os.environ.get("GAT_JWT_SECRET", "jwt-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7

# DB
DATABASE_URL = os.environ.get("GAT_DATABASE_URL", f"sqlite:///{ROOT_DIR / 'backend' / 'data' / 'gat.db'}")
# On Vercel: use /tmp (ephemeral) so we don't write to read-only filesystem
if os.environ.get("VERCEL"):
    _data_dir = Path("/tmp/gat_data")
    _data_dir.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = os.environ.get("GAT_DATABASE_URL", f"sqlite:////tmp/gat_data/gat.db")
    USER_STORAGE_BASE = Path("/tmp/gat_data/user_storage")
else:
    (ROOT_DIR / "backend" / "data").mkdir(parents=True, exist_ok=True)
    USER_STORAGE_BASE = ROOT_DIR / "backend" / "data" / "user_storage"

# Input validation
MAX_UPLOAD_BYTES = int(os.environ.get("GAT_MAX_UPLOAD_BYTES", 5 * 1024 * 1024))  # 5 MiB
def _allowed_extensions() -> frozenset:
    raw = os.environ.get("GAT_ALLOWED_EXTENSIONS", ".txt,.md,.csv,.pdf").lower().replace(" ", "")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return frozenset(p if p.startswith(".") else f".{p}" for p in parts)


ALLOWED_UPLOAD_EXTENSIONS = _allowed_extensions()
MAX_SEARCH_QUERY_LENGTH = int(os.environ.get("GAT_MAX_SEARCH_QUERY_LENGTH", 500))
MAX_KEYWORDS_MULTI = int(os.environ.get("GAT_MAX_KEYWORDS_MULTI", 20))

# Rate limits (per user): requests per window
RATE_LIMIT_UPLOAD_PER_MINUTE = int(os.environ.get("GAT_RATE_LIMIT_UPLOAD", 30))
RATE_LIMIT_SEARCH_PER_MINUTE = int(os.environ.get("GAT_RATE_LIMIT_SEARCH", 60))
RATE_LIMIT_WINDOW_SECONDS = 60
