import logging
from datetime import timedelta

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.api.serializers import user_out
from app.core.config import get_settings
from app.core.security import (ALGO, auth_limiter, create_access_token, hash_password, hash_token,
                               new_refresh_token, verify_password)
from app.db.session import get_db, utcnow
from app.models import RefreshToken, User

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = logging.getLogger("cinesphere.auth")
COOKIE = "refresh_token"


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9 \-]{7,15}$")
    password: str = Field(min_length=8, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9 \-]{7,15}$")


class PasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)


def _issue(db: Session, user: User, response: Response) -> dict:
    s = get_settings()
    raw, digest = new_refresh_token()
    db.add(RefreshToken(user_id=user.id, token_hash=digest, expires_at=utcnow() + timedelta(days=s.refresh_token_days)))
    db.commit()
    response.set_cookie(COOKIE, raw, httponly=True, samesite="lax", secure=s.cookie_secure,
                        max_age=s.refresh_token_days * 86400, path="/api/auth")
    return {"access_token": create_access_token(user.id, user.role), "user": user_out(user)}


@router.post("/register", status_code=201, dependencies=[Depends(auth_limiter)])
def register(data: RegisterIn, response: Response, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    # role is NEVER taken from the request: self-registration always creates a customer
    user = User(name=data.name.strip(), email=email, phone=data.phone, password_hash=hash_password(data.password), role="customer")
    db.add(user)
    db.commit()
    return _issue(db, user, response)


@router.post("/login", dependencies=[Depends(auth_limiter)])
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(403, "This account has been suspended")
    return _issue(db, user, response)


@router.post("/refresh")
def refresh(response: Response, refresh_token: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    if not refresh_token:
        raise HTTPException(401, "Not logged in")
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token)))
    if not row or row.revoked or row.expires_at < utcnow():
        raise HTTPException(401, "Session expired. Please log in again.")
    user = db.get(User, row.user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "Account not available")
    row.revoked = True  # rotation: every refresh token works once
    db.commit()
    return _issue(db, user, response)


@router.post("/logout", status_code=204)
def logout(response: Response, refresh_token: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    if refresh_token:
        db.execute(update(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token)).values(revoked=True))
        db.commit()
    response.delete_cookie(COOKIE, path="/api/auth")


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_out(user)


@router.patch("/me")
def update_me(data: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if data.name:
        user.name = data.name.strip()
    if data.phone is not None:
        user.phone = data.phone
    db.commit()
    return user_out(user)


@router.post("/change-password", status_code=204)
def change_password(data: PasswordIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(data.new_password)
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
    db.commit()


def _reset_token(user: User) -> str:
    s = get_settings()
    # embeds a slice of the current hash, so the token stops working once the password changes
    payload = {"sub": str(user.id), "purpose": "reset", "h": user.password_hash[-12:],
               "exp": utcnow() + timedelta(minutes=30)}
    return jwt.encode(payload, s.secret_key, algorithm=ALGO)


@router.post("/forgot-password", dependencies=[Depends(auth_limiter)])
def forgot_password(data: ForgotIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    out: dict = {"message": "If that email exists, a reset link has been sent."}
    if user and user.is_active:
        token = _reset_token(user)
        log.info("Password reset requested for user %s", user.id)  # token deliberately not logged
        if get_settings().env == "dev":  # no SMTP in dev: hand the token straight back
            out["dev_reset_token"] = token
    return out


@router.post("/reset-password", status_code=204, dependencies=[Depends(auth_limiter)])
def reset_password(data: ResetIn, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(data.token, get_settings().secret_key, algorithms=[ALGO])
        if payload.get("purpose") != "reset":
            raise ValueError
        user = db.get(User, int(payload["sub"]))
        if not user or user.password_hash[-12:] != payload["h"]:
            raise ValueError
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(400, "This reset link is invalid or has expired")
    user.password_hash = hash_password(data.new_password)
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
    db.commit()
