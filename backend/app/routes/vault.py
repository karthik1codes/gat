"""
Vault API: unlock, lock, status, statistics.
Keys only in memory; never stored in plaintext on server.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..routes.auth import get_current_user_id
from ..services.vault_service import (
    get_vault,
    lock_vault as do_lock_vault,
    get_vault_stats,
    check_inactivity_and_lock,
)

router = APIRouter(prefix="/api/vault", tags=["vault"])


class UnlockRequest(BaseModel):
    password: str


class VaultStatusResponse(BaseModel):
    state: str  # LOCKED | UNLOCKED
    initialized: bool  # True if vault password was ever set (salt exists)


@router.get("/status", response_model=VaultStatusResponse)
def vault_status(user: User = Depends(get_current_user_id)):
    """Returns LOCKED or UNLOCKED and whether vault has been created (initialized)."""
    check_inactivity_and_lock(user.id)
    vault = get_vault(user.id)
    initialized = user.vault_salt is not None
    return VaultStatusResponse(state=vault.get_state().value, initialized=initialized)


@router.post("/unlock")
def vault_unlock(
    body: UnlockRequest,
    user: User = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Unlock vault with password. Derives keys via scrypt + HKDF; keys kept in memory only.
    Salt persisted per user (not secret) for re-unlock.
    """
    if not body.password:
        raise HTTPException(status_code=400, detail="Password required")
    vault = get_vault(user.id)
    salt = user.vault_salt
    if salt is None:
        from crypto.kdf import generate_salt
        salt = generate_salt()
        vault.load_vault(body.password.encode("utf-8"), salt=salt, use_scrypt=True)
        user.vault_salt = salt
        db.commit()
    else:
        try:
            vault.load_vault(body.password.encode("utf-8"), salt=salt, use_scrypt=True)
        except ValueError as e:
            raise HTTPException(status_code=401, detail="Invalid password or salt")
    return {"state": "UNLOCKED"}


@router.post("/lock")
def vault_lock(user: User = Depends(get_current_user_id)):
    """Lock vault; clear all key material from memory."""
    do_lock_vault(user.id)
    return {"state": "LOCKED"}


@router.get("/stats")
def vault_stats(user: User = Depends(get_current_user_id)):
    """
    Metrics for dashboard: total encrypted files, total size, index size,
    encryption algorithm, KDF algorithm, iteration count, last unlock timestamp.
    """
    check_inactivity_and_lock(user.id)
    return get_vault_stats(user.id)


@router.get("/client-string-key")
def vault_client_string_key(user: User = Depends(get_current_user_id)):
    """
    Return the vault's client-side string encryption key (base64).
    Used only by Locate Encrypted File / Decrypt File Name — client-side string
    encrypt/decrypt; not related to SSE or document storage.
    Requires vault to be unlocked.
    """
    check_inactivity_and_lock(user.id)
    vault = get_vault(user.id)
    if not vault.is_unlocked():
        raise HTTPException(status_code=403, detail="Vault is locked. Unlock to use client-side string encryption.")
    keys = vault.get_keys()
    if not keys:
        raise HTTPException(status_code=403, detail="Vault keys not available.")
    import base64
    return {"key_base64": base64.urlsafe_b64encode(keys.k_filename_enc).decode("ascii").rstrip("=")}
