from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import AuditLog, User
from app.services.locking import ApiError

bearer = HTTPBearer(auto_error=False)


def _user_from_token(creds: HTTPAuthorizationCredentials | None, db: Session) -> User | None:
    if not creds:
        return None
    try:
        payload = decode_access_token(creds.credentials)
    except PyJWTError:
        raise HTTPException(401, "Session expired. Please log in again.")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(401, "Account not found or suspended")
    return user


def optional_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    return _user_from_token(creds, db)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    user = _user_from_token(creds, db)
    if not user:
        raise HTTPException(401, "Please log in to continue")
    return user


def require_roles(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:  # always checked on the server; the frontend role is cosmetic
            raise HTTPException(403, "You do not have permission to do this")
        return user
    return dep


admin_only = require_roles("admin")
staff_or_admin = require_roles("admin", "staff")


def audit(db: Session, actor: User, action: str, entity: str | None = None, entity_id=None, detail: dict | None = None):
    db.add(AuditLog(actor_id=actor.id, action=action, entity=entity, entity_id=str(entity_id) if entity_id is not None else None, detail=detail))


async def api_error_handler(_: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status, content={"code": exc.code, "detail": exc.message, "seat_ids": exc.seat_ids})
