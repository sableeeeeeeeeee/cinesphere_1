"""Server-side seat locking.

Atomicity comes from the database: UNIQUE(show_id, seat_id) on seat_locks and the partial
unique index on booking_seats. Python locks / frontend state are never relied upon, so this
is safe across multiple backend workers.
"""
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import utcnow
from app.models import BookingSeat, Seat, SeatLock, Show


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, seat_ids: list[int] | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.seat_ids = status, code, message, seat_ids or []


def cleanup_expired(db: Session, show_id: int | None = None) -> int:
    stmt = delete(SeatLock).where(SeatLock.expires_at <= utcnow())
    if show_id is not None:
        stmt = stmt.where(SeatLock.show_id == show_id)
    return db.execute(stmt).rowcount or 0


def get_bookable_show(db: Session, show_id: int) -> Show:
    show = db.get(Show, show_id)
    if not show:
        raise ApiError(404, "show_not_found", "Show not found")
    if show.status != "scheduled":
        raise ApiError(409, "show_cancelled", "This show has been cancelled")
    if show.movie.status != "published":
        raise ApiError(409, "movie_unavailable", "This movie is not available for booking")
    if show.starts_at <= utcnow():
        raise ApiError(409, "show_started", "This show has already started")
    return show


def acquire_locks(db: Session, show_id: int, user_id: int, session_id: str, seat_ids: list[int]) -> dict:
    cfg = get_settings()
    seat_ids = list(dict.fromkeys(seat_ids))
    if not seat_ids:
        raise ApiError(400, "no_seats", "Select at least one seat")
    show = get_bookable_show(db, show_id)

    seats = db.scalars(select(Seat).where(Seat.id.in_(seat_ids), Seat.screen_id == show.screen_id,
                                          Seat.is_active.is_(True))).all()
    if len(seats) != len(seat_ids):
        raise ApiError(400, "invalid_seat", "One or more seats do not exist for this show")
    unavailable = [s.id for s in seats if s.is_disabled]
    if unavailable:
        raise ApiError(409, "seat_unavailable", "One or more seats are not available", unavailable)
    if any(s.category not in show.prices for s in seats):
        raise ApiError(409, "seat_unpriced", "A selected seat category has no price for this show")

    cleanup_expired(db, show_id)

    booked = db.scalars(select(BookingSeat.seat_id).where(
        BookingSeat.show_id == show_id, BookingSeat.is_active.is_(True),
        BookingSeat.seat_id.in_(seat_ids))).all()
    if booked:
        db.rollback()
        raise ApiError(409, "seat_already_booked", "Seat already booked", list(booked))

    live = db.scalars(select(SeatLock).where(SeatLock.show_id == show_id, SeatLock.seat_id.in_(seat_ids))).all()
    mine_already = {l.seat_id for l in live if l.user_id == user_id and l.session_id == session_id}
    taken = [l.seat_id for l in live if l.seat_id not in mine_already]
    if taken:
        db.rollback()
        raise ApiError(409, "seat_already_locked", "Seat already locked by another customer", taken)

    held = db.scalars(select(SeatLock.seat_id).where(SeatLock.show_id == show_id, SeatLock.user_id == user_id,
                                                      SeatLock.session_id == session_id)).all()
    if len(set(held) | set(seat_ids)) > cfg.max_seats_per_booking:
        db.rollback()
        raise ApiError(400, "too_many_seats", f"You can select at most {cfg.max_seats_per_booking} seats")

    now = utcnow()
    for sid in seat_ids:
        if sid not in mine_already:
            db.add(SeatLock(show_id=show_id, seat_id=sid, user_id=user_id, session_id=session_id,
                            created_at=now, expires_at=now + timedelta(seconds=cfg.seat_lock_seconds)))
    try:
        db.commit()  # the UNIQUE constraint is the real arbiter if two requests raced past the checks
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "seat_already_locked", "Seat already locked by another customer", seat_ids)
    return my_locks(db, show_id, user_id, session_id)


def my_locks(db: Session, show_id: int, user_id: int, session_id: str) -> dict:
    now = utcnow()
    locks = db.scalars(select(SeatLock).where(
        SeatLock.show_id == show_id, SeatLock.user_id == user_id, SeatLock.session_id == session_id,
        SeatLock.expires_at > now)).all()
    expires = min((l.expires_at for l in locks), default=None)
    return {
        "seat_ids": [l.seat_id for l in locks],
        "expires_at": expires.isoformat() + "Z" if expires else None,
        "seconds_remaining": max(0, int((expires - now).total_seconds())) if expires else 0,
        "server_time": now.isoformat() + "Z",
    }


def release_locks(db: Session, show_id: int, user_id: int, session_id: str, seat_ids: list[int] | None = None) -> int:
    stmt = delete(SeatLock).where(SeatLock.show_id == show_id, SeatLock.user_id == user_id,
                                  SeatLock.session_id == session_id)
    if seat_ids:
        stmt = stmt.where(SeatLock.seat_id.in_(seat_ids))
    n = db.execute(stmt).rowcount or 0
    db.commit()
    return n
