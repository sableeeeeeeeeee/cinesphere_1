"""Password hashing, JWT helpers, and a tiny in-memory rate limiter."""
import hashlib
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, Request

from app.core.config import get_settings

ALGO = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: int, role: str) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=s.access_token_minutes)
    return jwt.encode({"sub": str(user_id), "role": role, "exp": exp}, s.secret_key, algorithm=ALGO)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, get_settings().secret_key, algorithms=[ALGO])


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw)


class RateLimiter:
    """Per-process sliding-window limiter. Use Redis/nginx in multi-worker production."""

    def __init__(self, limit: int, window: int):
        self.limit, self.window = limit, window
        self.hits: dict[str, deque] = defaultdict(deque)

    def __call__(self, request: Request):
        key = f"{request.client.host if request.client else 'x'}:{request.url.path}"
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            raise HTTPException(429, "Too many attempts. Please wait a minute and try again.")
        q.append(now)

    def reset(self):
        self.hits.clear()


auth_limiter = RateLimiter(limit=20, window=60)
