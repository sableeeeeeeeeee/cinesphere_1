from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import admin_only, audit, staff_or_admin
from app.api.serializers import (booking_out, cinema_out, food_item_out, food_order_out, iso, movie_out,
                                 screen_out, show_out, user_out)
from app.db.session import get_db, to_utc_naive, utcnow
from app.models import (AuditLog, Booking, BookingSeat, Cinema, Coupon, FoodCategory, FoodItem, FoodOrder, Genre,
                        Movie, Review, ReviewReport, Screen, Seat, SeatLock, Setting, Show, User)
from app.models.catalog import SEAT_CATEGORIES
from app.models.extras import FOOD_STATUSES
from app.services import booking as booking_svc
from app.services import layout as layout_svc
from app.services.layout import LayoutError

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ------------------------------------------------------------------ movies
class MovieIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    synopsis: str = ""
    poster_url: str | None = None
    backdrop_url: str | None = None
    trailer_url: str | None = None
    director: str | None = None
    cast: list[str] = []
    language: str = "English"
    duration_min: int = Field(120, ge=1, le=600)
    certificate: str = "UA"
    release_date: date | None = None
    status: str = Field("published", pattern="^(draft|published|archived)$")
    genres: list[str] = []


def _apply_movie(db: Session, m: Movie, data: dict):
    genres = data.pop("genres", None)
    for k, v in data.items():
        setattr(m, k, v)
    if genres is not None:
        objs = []
        for name in genres:
            g = db.scalar(select(Genre).where(Genre.name == name)) or Genre(name=name)
            objs.append(g)
        m.genres = objs


@router.get("/movies")
def admin_movies(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return [movie_out(m) for m in db.scalars(select(Movie).order_by(Movie.id.desc()))]


@router.post("/movies", status_code=201)
def create_movie(data: MovieIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    m = Movie()
    _apply_movie(db, m, data.model_dump())
    db.add(m)
    db.flush()
    audit(db, admin, "movie.create", "movie", m.id, {"title": m.title})
    db.commit()
    return movie_out(m)


@router.patch("/movies/{movie_id}")
def update_movie(movie_id: int, data: MovieIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    m = db.get(Movie, movie_id)
    if not m:
        raise HTTPException(404, "Movie not found")
    _apply_movie(db, m, data.model_dump())
    audit(db, admin, "movie.update", "movie", m.id)
    db.commit()
    return movie_out(m)


@router.delete("/movies/{movie_id}", status_code=204)
def archive_movie(movie_id: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    m = db.get(Movie, movie_id)
    if not m:
        raise HTTPException(404, "Movie not found")
    m.status = "archived"  # never hard-delete: bookings and reviews reference it
    audit(db, admin, "movie.archive", "movie", m.id)
    db.commit()


# ----------------------------------------------------- cinemas and screens
class CinemaIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    city: str = Field(min_length=1, max_length=80)
    address: str = ""
    phone: str | None = None
    amenities: list[str] = []
    is_active: bool = True


@router.get("/cinemas")
def admin_cinemas(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return [cinema_out(c, True) for c in db.scalars(select(Cinema).order_by(Cinema.id.desc()))]


@router.post("/cinemas", status_code=201)
def create_cinema(data: CinemaIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    c = Cinema(**data.model_dump())
    db.add(c)
    db.flush()
    audit(db, admin, "cinema.create", "cinema", c.id, {"name": c.name})
    db.commit()
    return cinema_out(c, True)


@router.patch("/cinemas/{cinema_id}")
def update_cinema(cinema_id: int, data: CinemaIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    c = db.get(Cinema, cinema_id)
    if not c:
        raise HTTPException(404, "Cinema not found")
    for k, v in data.model_dump().items():
        setattr(c, k, v)
    audit(db, admin, "cinema.update", "cinema", c.id)
    db.commit()
    return cinema_out(c, True)


class ScreenIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    label: str | None = None
    formats: list[str] = ["2D"]
    rows: int = Field(8, ge=1, le=layout_svc.MAX_ROWS)  # only used when creating (initial grid)
    cols: int = Field(12, ge=1, le=layout_svc.MAX_COLS)


@router.post("/cinemas/{cinema_id}/screens", status_code=201)
def create_screen(cinema_id: int, data: ScreenIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    if not db.get(Cinema, cinema_id):
        raise HTTPException(404, "Cinema not found")
    s = Screen(cinema_id=cinema_id, name=data.name, label=data.label, formats=data.formats)
    db.add(s)
    db.flush()
    layout_svc.apply_layout(db, s, layout_svc.default_layout(data.rows, data.cols))
    audit(db, admin, "screen.create", "screen", s.id)
    db.commit()
    return {**screen_out(s, True), "summary": layout_svc.layout_summary(s.layout)}


@router.get("/screens/{screen_id}")
def get_screen(screen_id: int, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    s = db.get(Screen, screen_id)
    if not s:
        raise HTTPException(404, "Screen not found")
    return {**screen_out(s, True), "summary": layout_svc.layout_summary(s.layout)}


@router.patch("/screens/{screen_id}")
def update_screen(screen_id: int, data: ScreenIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    s = db.get(Screen, screen_id)
    if not s:
        raise HTTPException(404, "Screen not found")
    s.name, s.label, s.formats = data.name, data.label, data.formats
    audit(db, admin, "screen.update", "screen", s.id)
    db.commit()
    return screen_out(s)


class LayoutIn(BaseModel):
    row_labels: list[str]
    cols: int
    cells: list[list[dict | None]]


@router.put("/screens/{screen_id}/layout")
def save_layout(screen_id: int, data: LayoutIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    s = db.get(Screen, screen_id)
    if not s:
        raise HTTPException(404, "Screen not found")
    try:
        summary = layout_svc.apply_layout(db, s, data.model_dump())
    except LayoutError as e:
        db.rollback()
        raise HTTPException(422, {"message": str(e), "errors": e.details})
    audit(db, admin, "screen.layout", "screen", s.id, summary)
    db.commit()
    return {**screen_out(s, True), "summary": summary}


@router.post("/screens/{screen_id}/duplicate", status_code=201)
def duplicate_screen(screen_id: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    src = db.get(Screen, screen_id)
    if not src:
        raise HTTPException(404, "Screen not found")
    s = Screen(cinema_id=src.cinema_id, name=f"{src.name} (copy)", label=src.label, formats=src.formats)
    db.add(s)
    db.flush()
    layout_svc.apply_layout(db, s, src.layout)
    audit(db, admin, "screen.duplicate", "screen", s.id, {"from": src.id})
    db.commit()
    return screen_out(s, True)


@router.delete("/screens/{screen_id}", status_code=204)
def delete_screen(screen_id: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    s = db.get(Screen, screen_id)
    if not s:
        raise HTTPException(404, "Screen not found")
    if db.scalar(select(func.count()).select_from(Show).where(Show.screen_id == s.id)):
        raise HTTPException(409, "This screen has shows scheduled or in history and cannot be deleted")
    db.delete(s)
    audit(db, admin, "screen.delete", "screen", screen_id)
    db.commit()


# ------------------------------------------------------------------- shows
class ShowIn(BaseModel):
    movie_id: int
    screen_id: int
    starts_at: datetime  # UTC (the frontend converts from the admin's local time)
    format: str = "2D"
    language: str = "English"
    prices: dict[str, int]  # {category: paise}


def _check_show(db: Session, data: ShowIn, exclude_id: int | None = None) -> tuple[Movie, Screen, datetime]:
    movie, screen = db.get(Movie, data.movie_id), db.get(Screen, data.screen_id)
    if not movie or not screen:
        raise HTTPException(404, "Movie or screen not found")
    start = to_utc_naive(data.starts_at)
    if start <= utcnow():
        raise HTTPException(422, "A show cannot be scheduled in the past")
    end = start + timedelta(minutes=movie.duration_min + 15)  # 15 min cleaning buffer
    clash = select(Show.id).where(Show.screen_id == screen.id, Show.status == "scheduled",
                                  Show.starts_at < end, Show.ends_at > start)
    if exclude_id:
        clash = clash.where(Show.id != exclude_id)
    if db.scalar(clash):
        raise HTTPException(409, "This screen already has a show that overlaps this time")
    cats = {c["c"] for row in (screen.layout or {}).get("cells", []) for c in row if c}
    missing = [c for c in cats if c not in data.prices]
    if missing or any(v < 0 for v in data.prices.values()) or any(k not in SEAT_CATEGORIES for k in data.prices):
        raise HTTPException(422, f"Prices required (>= 0) for every seat category on this screen: {', '.join(sorted(cats))}")
    return movie, screen, start


@router.get("/shows")
def admin_shows(movie_id: int | None = None, upcoming_only: bool = False, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    stmt = select(Show).order_by(Show.starts_at.desc()).limit(200)
    if movie_id:
        stmt = stmt.where(Show.movie_id == movie_id)
    if upcoming_only:
        stmt = stmt.where(Show.starts_at > utcnow())
    shows = db.scalars(stmt).all()
    sold = dict(db.execute(select(BookingSeat.show_id, func.count()).where(BookingSeat.is_active.is_(True)).group_by(BookingSeat.show_id)).all())
    return [{**show_out(s), "tickets_sold": sold.get(s.id, 0)} for s in shows]


@router.post("/shows", status_code=201)
def create_show(data: ShowIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    movie, screen, start = _check_show(db, data)
    s = Show(movie_id=movie.id, screen_id=screen.id, starts_at=start, ends_at=start + timedelta(minutes=movie.duration_min + 15),
             format=data.format, language=data.language, prices=data.prices)
    db.add(s)
    db.flush()
    audit(db, admin, "show.create", "show", s.id)
    db.commit()
    return show_out(s)


@router.patch("/shows/{show_id}")
def update_show(show_id: int, data: ShowIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    s = db.get(Show, show_id)
    if not s:
        raise HTTPException(404, "Show not found")
    has_bookings = db.scalar(select(func.count()).select_from(BookingSeat).where(BookingSeat.show_id == s.id, BookingSeat.is_active.is_(True)))
    if has_bookings and (data.movie_id != s.movie_id or data.screen_id != s.screen_id or to_utc_naive(data.starts_at) != s.starts_at):
        raise HTTPException(409, "Tickets are already sold: only prices, format and language can change. Cancel the show instead.")
    if has_bookings:
        s.format, s.language = data.format, data.language  # prices stay: sold tickets keep their snapshot, new buyers see new prices
        s.prices = data.prices
    else:
        movie, screen, start = _check_show(db, data, exclude_id=s.id)
        s.movie_id, s.screen_id, s.starts_at = movie.id, screen.id, start
        s.ends_at = start + timedelta(minutes=movie.duration_min + 15)
        s.format, s.language, s.prices = data.format, data.language, data.prices
    audit(db, admin, "show.update", "show", s.id)
    db.commit()
    return show_out(s)


@router.post("/shows/{show_id}/cancel")
def cancel_show(show_id: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    s = db.get(Show, show_id)
    if not s:
        raise HTTPException(404, "Show not found")
    s.status = "cancelled"
    db.query(SeatLock).filter(SeatLock.show_id == s.id).delete()
    db.flush()
    cancelled = 0
    for b in db.scalars(select(Booking).where(Booking.show_id == s.id, Booking.status == "confirmed")).all():
        booking_svc.cancel_booking(db, b, by_admin=True)  # full refund because the cinema cancelled
        cancelled += 1
    audit(db, admin, "show.cancel", "show", s.id, {"bookings_cancelled": cancelled})
    db.commit()
    return {"ok": True, "bookings_cancelled": cancelled}


@router.get("/shows/{show_id}/bookings")
def show_bookings(show_id: int, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return [booking_out(b) for b in db.scalars(select(Booking).where(Booking.show_id == show_id).order_by(Booking.created_at.desc()))]


# ---------------------------------------------------------------- bookings
@router.get("/bookings")
def admin_bookings(q: str | None = None, status: str | None = None, page: int = Query(1, ge=1), db: Session = Depends(get_db),
                   _: User = Depends(admin_only)):
    stmt = select(Booking).join(User, User.id == Booking.user_id).order_by(Booking.created_at.desc())
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Booking.reference.ilike(like), User.email.ilike(like), User.name.ilike(like)))
    if status:
        stmt = stmt.where(Booking.status == status)
    rows = db.scalars(stmt.offset((page - 1) * 25).limit(25)).all()
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_([b.user_id for b in rows])))} if rows else {}
    return [{**booking_out(b), "customer": users[b.user_id].name, "customer_email": users[b.user_id].email} for b in rows]


@router.post("/bookings/{booking_id}/cancel")
def admin_cancel(booking_id: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    b = db.get(Booking, booking_id)
    if not b:
        raise HTTPException(404, "Booking not found")
    booking_svc.cancel_booking(db, b, by_admin=True)  # goes through the same service: seats are released properly
    audit(db, admin, "booking.cancel", "booking", b.id, {"refund": b.refund_amount})
    db.commit()
    return booking_out(b)


# -------------------------------------------------------------------- food
class FoodItemIn(BaseModel):
    category: str
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    image_url: str | None = None
    price: int = Field(ge=0)
    sizes: list[dict] = []
    is_available: bool = True
    stock: int | None = Field(None, ge=0)


def _food_cat(db: Session, name: str) -> FoodCategory:
    c = db.scalar(select(FoodCategory).where(FoodCategory.name == name))
    if not c:
        c = FoodCategory(name=name, sort_order=99)
        db.add(c)
        db.flush()
    return c


@router.get("/food/items")
def admin_food_items(db: Session = Depends(get_db), _: User = Depends(staff_or_admin)):
    return [food_item_out(f) for f in db.scalars(select(FoodItem).order_by(FoodItem.id))]


@router.post("/food/items", status_code=201)
def create_food(data: FoodItemIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    d = data.model_dump()
    f = FoodItem(category_id=_food_cat(db, d.pop("category")).id, **d)
    db.add(f)
    db.flush()
    audit(db, admin, "food.create", "food_item", f.id)
    db.commit()
    return food_item_out(f)


@router.patch("/food/items/{item_id}")
def update_food(item_id: int, data: FoodItemIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    f = db.get(FoodItem, item_id)
    if not f:
        raise HTTPException(404, "Item not found")
    d = data.model_dump()
    f.category_id = _food_cat(db, d.pop("category")).id
    for k, v in d.items():
        setattr(f, k, v)
    audit(db, admin, "food.update", "food_item", f.id)
    db.commit()
    return food_item_out(f)


@router.get("/food/orders")
def admin_food_orders(status: str | None = None, db: Session = Depends(get_db), _: User = Depends(staff_or_admin)):
    stmt = select(FoodOrder).order_by(FoodOrder.created_at.desc()).limit(100)
    if status:
        stmt = stmt.where(FoodOrder.status == status)
    return [food_order_out(o) for o in db.scalars(stmt)]


class StatusIn(BaseModel):
    status: str


@router.patch("/food/orders/{order_id}")
def set_food_status(order_id: int, data: StatusIn, staff: User = Depends(staff_or_admin), db: Session = Depends(get_db)):
    if data.status not in FOOD_STATUSES:
        raise HTTPException(422, f"Status must be one of: {', '.join(FOOD_STATUSES)}")
    o = db.get(FoodOrder, order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    o.status = data.status
    booking_svc.notify(db, o.user_id, "Food order update", f"{o.order_number}: {data.status}")
    audit(db, staff, "food.order_status", "food_order", o.id, {"status": data.status})
    db.commit()
    return food_order_out(o)


# ----------------------------------------------------------------- reviews
@router.get("/reports")
def review_reports(status: str = "pending", db: Session = Depends(get_db), _: User = Depends(admin_only)):
    rows = db.scalars(select(ReviewReport).where(ReviewReport.status == status).order_by(ReviewReport.created_at.desc())).all()
    return [{"id": r.id, "reason": r.reason, "status": r.status, "created_at": iso(r.created_at),
             "review": {"id": r.review.id, "text": r.review.text, "rating": r.review.rating, "author": r.review.user.name,
                        "movie_id": r.review.movie_id, "is_removed": r.review.is_removed}} for r in rows]


@router.post("/reports/{report_id}/{action}")
def resolve_report(report_id: int, action: str, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    from app.api.customer import recompute_rating
    if action not in ("remove", "dismiss"):
        raise HTTPException(404, "Unknown action")
    r = db.get(ReviewReport, report_id)
    if not r:
        raise HTTPException(404, "Report not found")
    if action == "remove":
        r.review.is_removed = True
        for other in db.scalars(select(ReviewReport).where(ReviewReport.review_id == r.review_id)):
            other.status = "removed"
        db.flush()
        recompute_rating(db, r.review.movie_id)
    else:
        r.status = "dismissed"
    audit(db, admin, f"review.{action}", "review", r.review_id, {"report": r.id})
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ users
@router.get("/users")
def admin_users(q: str | None = None, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    stmt = select(User).order_by(User.id.desc()).limit(100)
    if q:
        stmt = stmt.where(or_(User.email.ilike(f"%{q}%"), User.name.ilike(f"%{q}%")))
    return [user_out(u) for u in db.scalars(stmt)]


class UserPatch(BaseModel):
    is_active: bool | None = None
    role: str | None = Field(None, pattern="^(customer|staff|admin)$")


@router.patch("/users/{user_id}")
def patch_user(user_id: int, data: UserPatch, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == admin.id:
        raise HTTPException(400, "You cannot change your own role or suspend yourself")
    if data.is_active is not None:
        u.is_active = data.is_active
    if data.role is not None:
        u.role = data.role  # only an existing admin can reach this line
    audit(db, admin, "user.update", "user", u.id, data.model_dump(exclude_none=True))
    db.commit()
    return user_out(u)


# ---------------------------------------------------------------- coupons
class CouponIn(BaseModel):
    code: str = Field(min_length=3, max_length=40)
    kind: str = Field(pattern="^(percent|fixed)$")
    value: int = Field(gt=0)
    max_discount: int | None = None
    min_order: int = 0
    max_uses: int | None = None
    expires_at: datetime | None = None
    movie_id: int | None = None
    cinema_id: int | None = None
    is_active: bool = True
    description: str = ""


@router.get("/coupons")
def list_coupons(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return [{**{c.name: getattr(x, c.name) for c in Coupon.__table__.columns if c.name != "expires_at"},
             "expires_at": iso(x.expires_at)} for x in db.scalars(select(Coupon).order_by(Coupon.id.desc()))]


@router.post("/coupons", status_code=201)
def create_coupon(data: CouponIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    if data.kind == "percent" and data.value > 100:
        raise HTTPException(422, "Percent discounts cannot exceed 100")
    d = data.model_dump()
    d["code"] = d["code"].strip().upper()
    if d["expires_at"] is not None:
        d["expires_at"] = d["expires_at"].replace(tzinfo=None)
    c = Coupon(**d)
    db.add(c)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A coupon with this code already exists")
    audit(db, admin, "coupon.create", "coupon", c.id)
    db.commit()
    return {"id": c.id, "code": c.code}


@router.patch("/coupons/{coupon_id}/active")
def toggle_coupon(coupon_id: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    c = db.get(Coupon, coupon_id)
    if not c:
        raise HTTPException(404, "Coupon not found")
    c.is_active = not c.is_active
    audit(db, admin, "coupon.toggle", "coupon", c.id, {"is_active": c.is_active})
    db.commit()
    return {"is_active": c.is_active}


# --------------------------------------------------------- settings / audit
class PolicyIn(BaseModel):
    tiers: list[dict]


@router.put("/cancellation-policy")
def set_policy(data: PolicyIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    for t in data.tiers:
        if not (isinstance(t.get("hours"), (int, float)) and isinstance(t.get("percent"), int) and 0 <= t["percent"] <= 100 and t["hours"] >= 0):
            raise HTTPException(422, "Each tier needs hours >= 0 and percent 0-100")
    row = db.get(Setting, "cancellation_policy")
    if row:
        row.value = data.model_dump()
    else:
        db.add(Setting(key="cancellation_policy", value=data.model_dump()))
    audit(db, admin, "policy.update", "setting", "cancellation_policy", data.model_dump())
    db.commit()
    return data.model_dump()


@router.get("/audit-logs")
def audit_logs(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)).all()
    return [{"id": a.id, "actor_id": a.actor_id, "action": a.action, "entity": a.entity, "entity_id": a.entity_id,
             "detail": a.detail, "created_at": iso(a.created_at)} for a in rows]


# ---------------------------------------------------------------- dashboard
@router.get("/stats")
def stats(date_from: date | None = None, date_to: date | None = None, cinema_id: int | None = None,
          movie_id: int | None = None, tz: int = Query(0, ge=-840, le=840), db: Session = Depends(get_db), _: User = Depends(admin_only)):
    """Every number comes from database rows. Gross = all bookings ever made; confirmed revenue
    excludes cancelled bookings; refunds are shown separately."""
    # `tz` = the admin's UTC offset in minutes (IST = 330). Bookings are stored in UTC, so the chosen local
    # days are converted to UTC boundaries, and per-day totals are bucketed by the admin's local day.
    offset = timedelta(minutes=tz)
    d_to = date_to or (utcnow() + offset).date()
    d_from = date_from or (d_to - timedelta(days=29))
    start = datetime.combine(d_from, datetime.min.time()) - offset
    end = datetime.combine(d_to + timedelta(days=1), datetime.min.time()) - offset

    def scoped(stmt):
        stmt = stmt.join(Show, Show.id == Booking.show_id).where(Booking.created_at >= start, Booking.created_at < end)
        if cinema_id:
            stmt = stmt.join(Screen, Screen.id == Show.screen_id).where(Screen.cinema_id == cinema_id)
        if movie_id:
            stmt = stmt.where(Show.movie_id == movie_id)
        return stmt

    gross, n_all = db.execute(scoped(select(func.coalesce(func.sum(Booking.total), 0), func.count(Booking.id)))).one()
    conf, n_conf = db.execute(scoped(select(func.coalesce(func.sum(Booking.total), 0), func.count(Booking.id)).where(Booking.status == "confirmed"))).one()
    refunds, n_canc = db.execute(scoped(select(func.coalesce(func.sum(Booking.refund_amount), 0), func.count(Booking.id)).where(Booking.status == "cancelled"))).one()
    tickets = db.execute(scoped(select(func.count(BookingSeat.id)).select_from(Booking).join(BookingSeat, BookingSeat.booking_id == Booking.id)
                                .where(Booking.status == "confirmed"))).scalar_one()

    buckets: dict = {}
    for created, total in db.execute(scoped(select(Booking.created_at, Booking.total).where(Booking.status == "confirmed"))).all():
        d = (created + offset).date().isoformat()
        rev, n = buckets.get(d, (0, 0))
        buckets[d] = (rev + total, n + 1)
    daily = [(d, r, n) for d, (r, n) in sorted(buckets.items())]
    popular = db.execute(scoped(select(Show.movie_id, func.count(BookingSeat.id)).select_from(Booking).join(BookingSeat, BookingSeat.booking_id == Booking.id)
                                .where(Booking.status == "confirmed")).group_by(Show.movie_id).order_by(func.count(BookingSeat.id).desc()).limit(8)).all()
    titles = {m.id: m.title for m in db.scalars(select(Movie).where(Movie.id.in_([p[0] for p in popular])))} if popular else {}
    by_cinema = db.execute(select(Cinema.name, func.coalesce(func.sum(Booking.total), 0)).select_from(Booking)
                           .join(Show, Show.id == Booking.show_id).join(Screen, Screen.id == Show.screen_id).join(Cinema, Cinema.id == Screen.cinema_id)
                           .where(Booking.status == "confirmed", Booking.created_at >= start, Booking.created_at < end,
                                  *( [Cinema.id == cinema_id] if cinema_id else []), *( [Show.movie_id == movie_id] if movie_id else []))
                           .group_by(Cinema.name)).all()

    now = utcnow()
    upcoming = db.scalars(select(Show).where(Show.starts_at > now, Show.status == "scheduled").order_by(Show.starts_at).limit(8)).all()
    sold = dict(db.execute(select(BookingSeat.show_id, func.count()).where(BookingSeat.is_active.is_(True)).group_by(BookingSeat.show_id)).all())
    caps = dict(db.execute(select(Seat.screen_id, func.count()).where(Seat.is_active.is_(True), Seat.is_disabled.is_(False)).group_by(Seat.screen_id)).all())
    occupancy = [{"show_id": s.id, "label": f"{s.movie.title[:18]} {s.starts_at:%d %b %H:%M}", "sold": sold.get(s.id, 0), "capacity": caps.get(s.screen_id, 0)} for s in upcoming]
    total_cap = sum(o["capacity"] for o in occupancy)

    food_total = db.scalar(select(func.coalesce(func.sum(FoodOrder.total), 0)).where(FoodOrder.created_at >= start, FoodOrder.created_at < end, FoodOrder.status != "cancelled"))
    food_orders = db.scalar(select(func.count()).select_from(FoodOrder).where(FoodOrder.created_at >= start, FoodOrder.created_at < end))
    return {
        "range": {"from": d_from.isoformat(), "to": d_to.isoformat()},
        "cards": {"gross_bookings_value": gross, "bookings_total": n_all, "confirmed_revenue": conf, "confirmed_bookings": n_conf,
                  "refunds": refunds, "cancelled_bookings": n_canc, "tickets_sold": tickets,
                  "active_movies": db.scalar(select(func.count()).select_from(Movie).where(Movie.status == "published")),
                  "customers": db.scalar(select(func.count()).select_from(User).where(User.role == "customer")),
                  "upcoming_shows": db.scalar(select(func.count()).select_from(Show).where(Show.starts_at > now, Show.status == "scheduled")),
                  "occupancy_percent": round(100 * sum(o["sold"] for o in occupancy) / total_cap, 1) if total_cap else 0,
                  "food_orders": food_orders, "food_sales": food_total,
                  "pending_reports": db.scalar(select(func.count()).select_from(ReviewReport).where(ReviewReport.status == "pending"))},
        "daily": [{"date": str(d), "revenue": r, "bookings": n} for d, r, n in daily],
        "popular_movies": [{"title": titles.get(m, str(m)), "tickets": n} for m, n in popular],
        "revenue_by_cinema": [{"cinema": c, "revenue": r} for c, r in by_cinema],
        "occupancy": occupancy,
    }
