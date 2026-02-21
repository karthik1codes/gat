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
# Ensure data dir exists
(ROOT_DIR / "backend" / "data").mkdir(parents=True, exist_ok=True)

# Per-user storage base for SSE
USER_STORAGE_BASE = ROOT_DIR / "backend" / "data" / "user_storage"
