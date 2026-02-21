"""Auth: Google token verification, JWT, key encryption."""
import hashlib
from base64 import urlsafe_b64encode
from datetime import datetime, timedelta
from typing import Optional

import jwt
from cryptography.fernet import Fernet

from .config import (
    GOOGLE_CLIENT_ID,
    SERVER_SECRET,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRE_DAYS,
)


def _get_fernet() -> Fernet:
    raw = SERVER_SECRET.encode() if isinstance(SERVER_SECRET, str) else SERVER_SECRET
    h = hashlib.sha256(raw).digest()
    return Fernet(urlsafe_b64encode(h))


def encrypt_sse_key(plain_key: bytes) -> bytes:
    """Encrypt SSE master key for storage (server-side secret)."""
    f = _get_fernet()
    return f.encrypt(plain_key)


def decrypt_sse_key(encrypted: bytes) -> bytes:
    """Decrypt stored SSE key."""
    f = _get_fernet()
    return f.decrypt(encrypted)


def create_jwt(user_id: str) -> str:
    exp = datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": user_id, "exp": exp, "iat": datetime.utcnow()},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def decode_jwt(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None


async def verify_google_token(id_token: str) -> Optional[dict]:
    """Verify Google id_token with tokeninfo and return payload (email, sub, name, picture) or None."""
    if not id_token or not GOOGLE_CLIENT_ID:
        return None
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token},
                timeout=10.0,
            )
        if r.status_code != 200:
            return None
        data = r.json()
        aud = data.get("aud")
        if aud != GOOGLE_CLIENT_ID:
            return None
        return {
            "sub": data.get("sub"),
            "email": data.get("email"),
            "name": data.get("name"),
            "picture": data.get("picture"),
        }
    except Exception:
        return None
