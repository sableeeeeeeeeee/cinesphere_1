from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.catalog import FoodLine
from app.api.deps import current_user, optional_user, staff_or_admin
from app.api.serializers import (booking_out, food_item_out, food_order_out, iso, movie_out, review_out)
from app.db.session import get_db, utcnow
from app.models import (Booking, BookingSeat, FoodCategory, FoodItem, FoodOrder, Movie, Notification, Review,
                        ReviewReport, ReviewVote, Show, User, Watchlist)
from app.services import booking as booking_svc
from app.services import locking

router = APIRouter(prefix="/api", tags=["customer"])


# ---------------------------------------------------------------- bookings
class CheckoutIn(BaseModel):
    show_id: int
    session_id: str = Field(min_length=8, max_length=64)
    seat_ids: list[int] = Field(min_length=1, max_length=20)
    idempotency_key: str = Field(min_length=8, max_length=64)
    food: list[FoodLine] = []
    coupon_code: str | None = None
    fulfilment: str = Field("pickup", pattern="^(pickup|seat_delivery)$")
    simulate_failure: bool = False  # development payment simulator only


@router.post("/bookings/checkout", status_code=201)
def checkout(data: CheckoutIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    b = booking_svc.checkout(db, user.id, show_id=data.show_id, session_id=data.session_id, seat_ids=data.seat_ids,
                             idempotency_key=data.idempotency_key, food=[f.model_dump() for f in data.food],
                             coupon_code=data.coupon_code, fulfilment=data.fulfilment,
                             simulate_failure=data.simulate_failure)
    return booking_out(b)


@router.get("/bookings/my")
def my_bookings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Booking).where(Booking.user_id == user.id).order_by(Booking.created_at.desc())).all()
    now = utcnow()
    out = {"upcoming": [], "past": [], "cancelled": []}
    for b in rows:
        key = "cancelled" if b.status == "cancelled" else ("upcoming" if b.starts_at > now else "past")
        out[key].append(booking_out(b))
    return out


def _own_booking(db: Session, booking_id: int, user: User) -> Booking:
    b = db.get(Booking, booking_id)
    if not b or (b.user_id != user.id and user.role not in ("admin", "staff")):
        raise HTTPException(404, "Booking not found")  # 404 (not 403) so references can't be probed
    return b


@router.get("/bookings/{booking_id}")
def booking_detail(booking_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    b = _own_booking(db, booking_id, user)
    orders = db.scalars(select(FoodOrder).where(FoodOrder.booking_id == b.id)).all()
    return {**booking_out(b), "food_orders": [food_order_out(o) for o in orders]}


@router.post("/bookings/{booking_id}/cancel")
def cancel(booking_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    b = db.get(Booking, booking_id)
    if not b or b.user_id != user.id:
        raise HTTPException(404, "Booking not found")
    return booking_out(booking_svc.cancel_booking(db, b))


@router.get("/cancellation-policy")
def policy(db: Session = Depends(get_db)):
    return booking_svc.get_policy(db)


class ValidateIn(BaseModel):
    reference: str


@router.post("/tickets/validate")
def validate_ticket(data: ValidateIn, staff: User = Depends(staff_or_admin), db: Session = Depends(get_db)):
    """Staff scan/enter the booking reference (the QR encodes it). Marks the ticket as used atomically."""
    ref = data.reference.strip().upper()
    b = db.scalar(select(Booking).where(Booking.reference == ref))
    if not b:
        return {"valid": False, "reason": "Ticket not found"}
    info = {"reference": b.reference, "movie_title": b.movie_title, "starts_at": iso(b.starts_at),
            "seats": [s.label for s in b.seats if s.is_active]}
    if b.status != "confirmed":
        return {"valid": False, "reason": "Booking was cancelled", **info}
    if b.checked_in_at:
        return {"valid": False, "reason": "Ticket already used", "used_at": iso(b.checked_in_at), **info}
    b.checked_in_at = utcnow()
    db.commit()
    return {"valid": True, "reason": "Entry allowed", **info}


# ----------------------------------------------------------------- reviews
class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: str = Field("", max_length=2000)


def _verified_ids(db: Session, movie_id: int, user_ids: list[int]) -> set[int]:
    """Verified = the user holds a confirmed, non-cancelled booking for this movie whose show has already started."""
    if not user_ids:
        return set()
    rows = db.scalars(select(Booking.user_id).join(Show, Show.id == Booking.show_id)
                      .where(Booking.user_id.in_(user_ids), Booking.status == "confirmed", Show.movie_id == movie_id,
                             Show.starts_at <= utcnow()).distinct())
    return set(rows)


def recompute_rating(db: Session, movie_id: int):
    avg, n = db.execute(select(func.avg(Review.rating), func.count()).where(Review.movie_id == movie_id, Review.is_removed.is_(False))).one()
    m = db.get(Movie, movie_id)
    m.avg_rating, m.rating_count = float(avg or 0), n


@router.get("/movies/{movie_id}/reviews")
def list_reviews(movie_id: int, sort: str = Query("newest", pattern="^(newest|highest|helpful)$"),
                 page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50),
                 user: User | None = Depends(optional_user), db: Session = Depends(get_db)):
    base = select(Review).where(Review.movie_id == movie_id, Review.is_removed.is_(False))
    order = {"newest": Review.created_at.desc(), "highest": Review.rating.desc(), "helpful": Review.helpful_count.desc()}[sort]
    items = db.scalars(base.order_by(order, Review.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    dist = dict(db.execute(select(Review.rating, func.count()).where(Review.movie_id == movie_id, Review.is_removed.is_(False))
                           .group_by(Review.rating)).all())
    total = sum(dist.values())
    verified = _verified_ids(db, movie_id, [r.user_id for r in items])
    m = db.get(Movie, movie_id)
    return {"items": [review_out(r, r.user_id in verified, bool(user and user.id == r.user_id)) for r in items],
            "total": total, "avg_rating": round(m.avg_rating or 0, 1) if m else 0,
            "distribution": {str(i): dist.get(i, 0) for i in range(1, 6)}}


@router.post("/movies/{movie_id}/reviews", status_code=201)
def create_review(movie_id: int, data: ReviewIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not db.get(Movie, movie_id):
        raise HTTPException(404, "Movie not found")
    r = Review(movie_id=movie_id, user_id=user.id, rating=data.rating, text=data.text.strip())
    db.add(r)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "You have already reviewed this movie. Edit your existing review instead.")
    recompute_rating(db, movie_id)
    db.commit()
    return review_out(r, user.id in _verified_ids(db, movie_id, [user.id]), True)


@router.patch("/reviews/{review_id}")
def edit_review(review_id: int, data: ReviewIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(Review, review_id)
    if not r or r.user_id != user.id or r.is_removed:
        raise HTTPException(404, "Review not found")
    r.rating, r.text, r.updated_at = data.rating, data.text.strip(), utcnow()
    recompute_rating(db, r.movie_id)
    db.commit()
    return review_out(r, user.id in _verified_ids(db, r.movie_id, [user.id]), True)


@router.delete("/reviews/{review_id}", status_code=204)
def delete_review(review_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(Review, review_id)
    if not r or (r.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Review not found")
    movie_id = r.movie_id
    db.delete(r)
    db.flush()
    recompute_rating(db, movie_id)
    db.commit()


@router.post("/reviews/{review_id}/helpful")
def helpful(review_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(Review, review_id)
    if not r or r.is_removed:
        raise HTTPException(404, "Review not found")
    if r.user_id == user.id:
        raise HTTPException(400, "You cannot vote on your own review")
    existing = db.scalar(select(ReviewVote).where(ReviewVote.review_id == review_id, ReviewVote.user_id == user.id))
    if existing:
        db.delete(existing)
        r.helpful_count = max(0, r.helpful_count - 1)
    else:
        db.add(ReviewVote(review_id=review_id, user_id=user.id))
        r.helpful_count += 1
    db.commit()
    return {"helpful_count": r.helpful_count, "voted": existing is None}


class ReportIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


@router.post("/reviews/{review_id}/report", status_code=201)
def report_review(review_id: int, data: ReportIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not db.get(Review, review_id):
        raise HTTPException(404, "Review not found")
    db.add(ReviewReport(review_id=review_id, user_id=user.id, reason=data.reason))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "You have already reported this review")
    return {"ok": True}


# -------------------------------------------------------------------- food
@router.get("/food/items")
def food_items(db: Session = Depends(get_db)):
    cats = db.scalars(select(FoodCategory).order_by(FoodCategory.sort_order)).all()
    items = db.scalars(select(FoodItem).order_by(FoodItem.id)).all()
    return [{"id": c.id, "name": c.name, "items": [food_item_out(i) for i in items if i.category_id == c.id]} for c in cats]


class FoodOrderIn(BaseModel):
    items: list[FoodLine] = Field(min_length=1)
    fulfilment: str = Field("pickup", pattern="^(pickup|seat_delivery)$")


@router.post("/food/orders", status_code=201)
def create_food_order(data: FoodOrderIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    o = booking_svc.place_food_order(db, user.id, [i.model_dump() for i in data.items], data.fulfilment)
    return food_order_out(o)


@router.get("/food/orders/my")
def my_food_orders(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [food_order_out(o) for o in db.scalars(select(FoodOrder).where(FoodOrder.user_id == user.id).order_by(FoodOrder.created_at.desc()))]


# ------------------------------------------------- watchlist, notifications
@router.get("/watchlist")
def get_watchlist(user: User = Depends(current_user), db: Session = Depends(get_db)):
    movies = db.scalars(select(Movie).join(Watchlist, Watchlist.movie_id == Movie.id).where(Watchlist.user_id == user.id)).all()
    return [movie_out(m) for m in movies]


@router.post("/watchlist/{movie_id}")
def toggle_watchlist(movie_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(Watchlist).where(Watchlist.user_id == user.id, Watchlist.movie_id == movie_id))
    if row:
        db.delete(row)
    else:
        if not db.get(Movie, movie_id):
            raise HTTPException(404, "Movie not found")
        db.add(Watchlist(user_id=user.id, movie_id=movie_id))
    db.commit()
    return {"saved": row is None}


@router.get("/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(50)).all()
    return [{"id": n.id, "title": n.title, "body": n.body, "is_read": n.is_read, "created_at": iso(n.created_at)} for n in rows]


@router.post("/notifications/read-all", status_code=204)
def read_all(user: User = Depends(current_user), db: Session = Depends(get_db)):
    for n in db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False))):
        n.is_read = True
    db.commit()
