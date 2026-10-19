import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import admin, auth, catalog, customer
from app.api.deps import api_error_handler
from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine, get_db, utcnow
from app.models import Coupon
from app.services.locking import ApiError, cleanup_expired

log = logging.getLogger("cinesphere")
settings = get_settings()


async def _expiry_loop():
    """Housekeeping only: correctness never depends on this, because every lock check also compares expires_at."""
    while True:
        await asyncio.sleep(30)
        try:
            with SessionLocal() as db:
                cleanup_expired(db)
                db.commit()
        except Exception:  # noqa
            log.exception("lock cleanup failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)  # PostgreSQL uses Alembic migrations instead
    if settings.seed_demo_on_start:
        from app.seed import seed  # no-op when the database already has users
        with SessionLocal() as db:
            seed(db)
    task = asyncio.create_task(_expiry_loop())
    yield
    task.cancel()


app = FastAPI(title=f"{settings.app_name} API", version="1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.add_exception_handler(ApiError, api_error_handler)
for r in (auth.router, catalog.router, customer.router, admin.router):
    app.include_router(r)


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("Unhandled error")  # full trace goes to the server log only
    return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/offers")
def offers(db: Session = Depends(get_db)):
    now = utcnow()
    rows = db.scalars(select(Coupon).where(Coupon.is_active.is_(True))).all()
    return [{"code": c.code, "description": c.description, "kind": c.kind, "value": c.value}
            for c in rows if not c.expires_at or c.expires_at > now]
