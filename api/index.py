"""
Vercel serverless entrypoint: expose FastAPI app for /api/* routes.
Rewrites pass originalPath in query; this middleware restores it so FastAPI sees the real path.
"""
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode

# Project root (parent of api/)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("VERCEL", "1")

from backend.app.main import app as _app


def _path_restore_middleware(app):
    """ASGI middleware: when originalPath is in query (Vercel rewrite), use it as the path."""
    async def wrapper(scope, receive, send):
        if scope.get("type") != "http":
            await app(scope, receive, send)
            return
        qs = scope.get("query_string", b"").decode("latin-1")
        params = parse_qs(qs)
        if "originalPath" in params and params["originalPath"]:
            path = params["originalPath"][0]
            if path.startswith("/"):
                scope = dict(scope)
                scope["path"] = path
                scope["raw_path"] = path.encode("utf-8")
                # Remove originalPath from query so the app does not see it
                params = {k: v for k, v in params.items() if k != "originalPath"}
                scope["query_string"] = urlencode(params, doseq=True).encode("utf-8")
        await app(scope, receive, send)
    return wrapper


app = _path_restore_middleware(_app)