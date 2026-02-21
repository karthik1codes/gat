"""Auth routes: Google login only."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..auth_utils import verify_google_token, create_jwt, decode_jwt
from ..sse_service import get_or_create_sse_client

router = APIRouter(prefix="/api/auth", tags=["auth"])


class GoogleTokenRequest(BaseModel):
    id_token: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None
    picture: str | None


@router.post("/google", response_model=AuthResponse)
async def google_login(body: GoogleTokenRequest, db: Session = Depends(get_db)):
    payload = await verify_google_token(body.id_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    google_id = payload["sub"]
    email = payload.get("email") or ""
    name = payload.get("name")
    picture = payload.get("picture")

    user = db.query(User).filter(User.google_id == google_id).first()
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            google_id=google_id,
            email=email,
            name=name,
            picture=picture,
        )
        client, encrypted_key = get_or_create_sse_client(user.id, None)
        user.sse_key_encrypted = encrypted_key
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        db.refresh(user)

    access_token = create_jwt(user.id)
    return AuthResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
        },
    )


def get_current_user_id(
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.split(" ", 1)[1]
    user_id = decode_jwt(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/me", response_model=UserResponse)
def auth_me(user: User = Depends(get_current_user_id)):
    return UserResponse(id=user.id, email=user.email, name=user.name, picture=user.picture)
