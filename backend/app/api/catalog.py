from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, optional_user
from app.api.serializers import cinema_out, iso, movie_out, screen_out, show_out
from app.db.session import get_db, utcnow
from app.models import (Booking, BookingSeat, Cinema, Genre, Movie, Screen, Seat, SeatLock, Show, User,
                        movie_genres)
from app.services import booking as booking_svc
from app.services import locking
from app.services.locking import ApiError

router = APIRouter(prefix="/api", tags=["catalog"])


# ------------------------------------------------------------------ movies
@router.get("/genres")
def genres(db: Session = Depends(get_db)):
    return [g.name for g in db.scalars(select(Genre).order_by(Genre.name))]


@router.get("/movies")
def list_movies(q: str | None = None, language: str | None = None, genre: str | None = None,
                release: str | None = Query(None, pattern="^(now_showing|coming_soon)$"),
                min_rating: float | None = None, sort: str = Query("newest", pattern="^(newest|rating|trending|title)$"),
                page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=50), db: Session = Depends(get_db)):
    stmt = select(Movie).where(Movie.status == "published")
    if q:
        stmt = stmt.where(Movie.title.ilike(f"%{q.strip()}%"))
    if language:
        stmt = stmt.where(Movie.language == language)
    if genre:
        stmt = stmt.where(Movie.id.in_(select(movie_genres.c.movie_id).join(Genre).where(Genre.name == genre)))
    if min_rating:
        stmt = stmt.where(Movie.avg_rating >= min_rating)
    today = date.today()
    if release == "now_showing":
        stmt = stmt.where(or_(Movie.release_date.is_(None), Movie.release_date <= today))
    elif release == "coming_soon":
        stmt = stmt.where(Movie.release_date > today)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    if sort == "rating":
        stmt = stmt.order_by(Movie.avg_rating.desc(), Movie.rating_count.desc())
    elif sort == "title":
        stmt = stmt.order_by(Movie.title)
    elif sort == "trending":
        sales = (select(Show.movie_id, func.count(BookingSeat.id).label("n")).join(BookingSeat, BookingSeat.show_id == Show.id)
                 .where(BookingSeat.is_active.is_(True)).group_by(Show.movie_id).subquery())
        stmt = stmt.outerjoin(sales, sales.c.movie_id == Movie.id).order_by(func.coalesce(sales.c.n, 0).desc(), Movie.id)
    else:
        stmt = stmt.order_by(Movie.release_date.desc().nullslast(), Movie.id.desc())
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [movie_out(m) for m in items], "total": total, "page": page, "page_size": page_size}


@router.get("/movies/{movie_id}")
def movie_detail(movie_id: int, db: Session = Depends(get_db)):
    m = db.get(Movie, movie_id)
    if not m or m.status != "published":
        raise HTTPException(404, "Movie not found")
    genre_ids = [g.id for g in m.genres]
    similar = []
    if genre_ids:
        similar = db.scalars(select(Movie).where(
            Movie.status == "published", Movie.id != m.id,
            Movie.id.in_(select(movie_genres.c.movie_id).where(movie_genres.c.genre_id.in_(genre_ids))))
            .order_by(Movie.avg_rating.desc()).limit(6)).all()
    return {**movie_out(m), "similar": [movie_out(s) for s in similar]}


# ----------------------------------------------------------------- cinemas
@router.get("/cities")
def cities(db: Session = Depends(get_db)):
    return [c for c in db.scalars(select(Cinema.city).where(Cinema.is_active.is_(True)).distinct().order_by(Cinema.city))]


@router.get("/cinemas")
def list_cinemas(city: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Cinema).where(Cinema.is_active.is_(True)).order_by(Cinema.name)
    if city:
        stmt = stmt.where(Cinema.city == city)
    return [cinema_out(c, True) for c in db.scalars(stmt)]


@router.get("/cinemas/{cinema_id}/screens")
def cinema_screens(cinema_id: int, db: Session = Depends(get_db)):
    c = db.get(Cinema, cinema_id)
    if not c:
        raise HTTPException(404, "Cinema not found")
    return [screen_out(s) for s in c.screens]


# ------------------------------------------------------------------- shows
def _availability(db: Session, show_ids: list[int]) -> dict[int, tuple[int, int]]:
    if not show_ids:
        return {}
    now = utcnow()
    shows = db.scalars(select(Show).where(Show.id.in_(show_ids))).all()
    totals = dict(db.execute(select(Seat.screen_id, func.count()).where(Seat.is_active.is_(True), Seat.is_disabled.is_(False))
                             .group_by(Seat.screen_id)).all())
    booked = dict(db.execute(select(BookingSeat.show_id, func.count()).where(BookingSeat.show_id.in_(show_ids), BookingSeat.is_active.is_(True))
                             .group_by(BookingSeat.show_id)).all())
    locked = dict(db.execute(select(SeatLock.show_id, func.count()).where(SeatLock.show_id.in_(show_ids), SeatLock.expires_at > now)
                             .group_by(SeatLock.show_id)).all())
    return {s.id: (max(0, totals.get(s.screen_id, 0) - booked.get(s.id, 0) - locked.get(s.id, 0)), totals.get(s.screen_id, 0))
            for s in shows}


@router.get("/shows")
def list_shows(movie_id: int | None = None, cinema_id: int | None = None, city: str | None = None,
               on_date: date | None = Query(None, alias="date"), tz: int = 0, db: Session = Depends(get_db)):
    """`tz` = client's UTC offset in minutes (IST = 330) so 'date' means the customer's local day."""
    stmt = (select(Show).join(Screen, Screen.id == Show.screen_id).join(Cinema, Cinema.id == Screen.cinema_id)
            .where(Show.status == "scheduled", Show.starts_at > utcnow(), Cinema.is_active.is_(True)).order_by(Show.starts_at))
    if movie_id:
        stmt = stmt.where(Show.movie_id == movie_id)
    if cinema_id:
        stmt = stmt.where(Cinema.id == cinema_id)
    if city:
        stmt = stmt.where(Cinema.city == city)
    if on_date:
        start = datetime.combine(on_date, datetime.min.time()) - timedelta(minutes=tz)
        stmt = stmt.where(Show.starts_at >= start, Show.starts_at < start + timedelta(days=1))
    shows = db.scalars(stmt.limit(300)).all()
    avail = _availability(db, [s.id for s in shows])
    return [show_out(s, *avail[s.id]) for s in shows]


@router.get("/shows/{show_id}")
def show_detail(show_id: int, db: Session = Depends(get_db)):
    s = db.get(Show, show_id)
    if not s:
        raise HTTPException(404, "Show not found")
    a = _availability(db, [s.id])[s.id]
    return show_out(s, *a)


# -------------------------------------------------------------- seat map
@router.get("/shows/{show_id}/seats")
def seat_map(show_id: int, session_id: str | None = None, user: User | None = Depends(optional_user),
             db: Session = Depends(get_db)):
    """Polled by the seat page (every few seconds) so everyone sees locks/bookings from other customers."""
    show = db.get(Show, show_id)
    if not show:
        raise HTTPException(404, "Show not found")
    now = utcnow()
    seats = db.scalars(select(Seat).where(Seat.screen_id == show.screen_id, Seat.is_active.is_(True))).all()
    booked = set(db.scalars(select(BookingSeat.seat_id).where(BookingSeat.show_id == show_id, BookingSeat.is_active.is_(True))))
    locks = {l.seat_id: l for l in db.scalars(select(SeatLock).where(SeatLock.show_id == show_id, SeatLock.expires_at > now))}
    out = []
    for s in seats:
        if s.is_disabled:
            status = "disabled"
        elif s.id in booked:
            status = "booked"
        elif s.id in locks:
            l = locks[s.id]
            status = "mine" if (user and l.user_id == user.id and l.session_id == session_id) else "locked"
        else:
            status = "available"
        out.append({"id": s.id, "row": s.row_label, "number": s.number_label, "grid_row": s.grid_row,
                    "grid_col": s.grid_col, "category": s.category, "price": show.prices.get(s.category),
                    "status": status})
    mine = locking.my_locks(db, show_id, user.id, session_id) if (user and session_id) else None
    layout = show.screen.layout or {}
    return {"show": show_out(show), "row_labels": layout.get("row_labels", []), "cols": layout.get("cols", 0),
            "seats": out, "my_locks": mine, "server_time": iso(now)}


class LockIn(BaseModel):
    seat_ids: list[int] = Field(min_length=1, max_length=20)
    session_id: str = Field(min_length=8, max_length=64)


@router.post("/shows/{show_id}/locks", status_code=201)
def lock_seats(show_id: int, data: LockIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return locking.acquire_locks(db, show_id, user.id, data.session_id, data.seat_ids)


@router.delete("/shows/{show_id}/locks")
def unlock_seats(show_id: int, session_id: str, seat_ids: list[int] = Query(default=[]),
                 user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Release some seats (seat_ids) or, with none given, every hold of this session for the show."""
    locking.release_locks(db, show_id, user.id, session_id, seat_ids or None)
    return locking.my_locks(db, show_id, user.id, session_id)


class FoodLine(BaseModel):
    item_id: int
    quantity: int = Field(ge=1, le=20)
    size: str | None = None


class QuoteIn(BaseModel):
    seat_ids: list[int] = Field(min_length=1)
    food: list[FoodLine] = []
    coupon_code: str | None = None


@router.post("/shows/{show_id}/quote")
def quote(show_id: int, data: QuoteIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    show = locking.get_bookable_show(db, show_id)
    q = booking_svc.quote(db, show, data.seat_ids, [f.model_dump() for f in data.food], data.coupon_code, user.id)
    return booking_svc.quote_public(q)
