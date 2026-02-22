"""
Vault API: list/create vaults, unlock, lock, status, statistics.
Keys only in memory; never stored in plaintext on server.
Multi-vault: each vault has id, name, salt, verifier; user has current_vault_id.
"""

import sys
import subprocess
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Vault
from ..routes.auth import get_current_user_id
from ..services.vault_service import (
    get_vault,
    get_storage_dir,
    lock_vault as do_lock_vault,
    get_vault_stats,
    check_inactivity_and_lock,
)

router = APIRouter(prefix="/api/vault", tags=["vault"])
router_vaults = APIRouter(prefix="/api/vaults", tags=["vaults"])


# --- Multi-vault: list and create ---

class CreateVaultRequest(BaseModel):
    name: str
    password: str


class VaultListItem(BaseModel):
    id: str
    name: str
    created_at: str


@router_vaults.get("", response_model=list[VaultListItem])
def list_vaults(user: User = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """List all vaults for the current user (id, name, created_at). No secrets."""
    rows = db.query(Vault).filter(Vault.user_id == user.id).order_by(Vault.created_at.desc()).all()
    return [
        VaultListItem(
            id=v.id,
            name=v.name,
            created_at=v.created_at.isoformat() if v.created_at else "",
        )
        for v in rows
    ]


@router_vaults.post("", status_code=201)
def create_vault(
    body: CreateVaultRequest,
    user: User = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Create a new vault with name and password. Password is required and stored as salt+verifier.
    Creates storage dir and unlocks the new vault, setting it as current.
    """
    if not (body.name or "").strip():
        raise HTTPException(status_code=400, detail="Vault name required")
    if not (body.password or "").strip():
        raise HTTPException(status_code=400, detail="Password required")
    vault_id = str(uuid.uuid4())
    vm = get_vault(user.id, vault_id)
    result = vm.load_vault(body.password.encode("utf-8"), salt=None, use_scrypt=True)
    salt, verifier = result
    db.add(Vault(id=vault_id, user_id=user.id, name=body.name.strip(), salt=salt, verifier=verifier))
    user.current_vault_id = vault_id
    db.commit()
    storage_dir = get_storage_dir(user.id, vault_id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    (storage_dir / "documents").mkdir(exist_ok=True)
    return {"id": vault_id, "name": body.name.strip(), "state": "UNLOCKED"}


# --- Unlock / status / lock / stats (current vault) ---

class UnlockRequest(BaseModel):
    password: str
    vault_id: str | None = None  # if set, unlock this vault and set as current


class VaultStatusResponse(BaseModel):
    state: str  # LOCKED | UNLOCKED
    initialized: bool  # True if user has at least one vault
    current_vault_id: str | None = None
    current_vault_name: str | None = None


def _current_vault_or_403(user: User, db: Session) -> Vault:
    if not user.current_vault_id:
        raise HTTPException(status_code=403, detail="No vault selected. Create or open a vault.")
    v = db.query(Vault).filter(Vault.id == user.current_vault_id, Vault.user_id == user.id).first()
    if not v:
        raise HTTPException(status_code=403, detail="Current vault not found.")
    return v


@router.get("/status", response_model=VaultStatusResponse)
def vault_status(
    user: User = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Returns LOCKED/UNLOCKED for current vault and whether user has any vaults."""
    has_any = db.query(Vault).filter(Vault.user_id == user.id).first() is not None
    if not user.current_vault_id:
        return VaultStatusResponse(state="LOCKED", initialized=has_any, current_vault_id=None, current_vault_name=None)
    check_inactivity_and_lock(user.id, user.current_vault_id)
    vault = get_vault(user.id, user.current_vault_id)
    v = db.query(Vault).filter(Vault.id == user.current_vault_id).first()
    return VaultStatusResponse(
        state=vault.get_state().value,
        initialized=has_any,
        current_vault_id=user.current_vault_id,
        current_vault_name=v.name if v else None,
    )


@router.post("/unlock")
def vault_unlock(
    body: UnlockRequest,
    user: User = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Unlock a vault with password. If vault_id is provided, unlock that vault and set as current.
    Otherwise unlock current_vault_id. Sets current_vault_id when unlocking by vault_id.
    """
    if not body.password:
        raise HTTPException(status_code=400, detail="Password required")
    vault_id = body.vault_id or user.current_vault_id
    if not vault_id:
        raise HTTPException(status_code=400, detail="No vault selected. Provide vault_id or create a vault first.")
    v = db.query(Vault).filter(Vault.id == vault_id, Vault.user_id == user.id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vault not found")
    vm = get_vault(user.id, v.id)
    try:
        vm.load_vault(
            body.password.encode("utf-8"),
            salt=v.salt,
            use_scrypt=True,
            stored_verifier=v.verifier,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid password")
    user.current_vault_id = v.id
    db.commit()
    return {"state": "UNLOCKED", "vault_id": v.id, "vault_name": v.name}


@router.post("/lock")
def vault_lock(user: User = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Lock current vault and clear key material; clear current_vault_id."""
    if user.current_vault_id:
        do_lock_vault(user.id, user.current_vault_id)
        user.current_vault_id = None
        db.commit()
    return {"state": "LOCKED"}


@router.get("/stats")
def vault_stats(user: User = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Metrics for current vault (total files, size, index size, etc.)."""
    v = _current_vault_or_403(user, db)
    check_inactivity_and_lock(user.id, v.id)
    return get_vault_stats(user.id, v.id)


@router.get("/client-string-key")
def vault_client_string_key(user: User = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Return current vault's client-side string encryption key (base64). Requires vault unlocked."""
    v = _current_vault_or_403(user, db)
    check_inactivity_and_lock(user.id, v.id)
    vault = get_vault(user.id, v.id)
    if not vault.is_unlocked():
        raise HTTPException(status_code=403, detail="Vault is locked. Unlock to use client-side string encryption.")
    keys = vault.get_keys()
    if not keys:
        raise HTTPException(status_code=403, detail="Vault keys not available.")
    import base64
    return {"key_base64": base64.urlsafe_b64encode(keys.k_filename_enc).decode("ascii").rstrip("=")}


CRYPTOMATOR_EXE = r"C:\Program Files\Cryptomator\Cryptomator.exe"


@router.post("/reveal-drive")
def reveal_drive(user: User = Depends(get_current_user_id)):
    """
    Start Cryptomator on the server machine (e.g. run exe in background).
    Only the fixed path is used; safe to call when backend runs locally.
    """
    if sys.platform != "win32":
        raise HTTPException(status_code=501, detail="Reveal drive is only supported on Windows.")
    try:
        subprocess.Popen([CRYPTOMATOR_EXE])
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Cryptomator not found at default path.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True}
