"""Pricing, checkout, and cancellation. All money is integer paise and computed server-side."""
import secrets
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import utcnow
from app.models import (Booking, BookingSeat, Coupon, CouponUsage, FoodItem, FoodOrder, FoodOrderItem,
                        Notification, Payment, Refund, Seat, SeatLock, Setting, Show)
from app.services.locking import ApiError, cleanup_expired, get_bookable_show

DEFAULT_POLICY = {"tiers": [{"hours": 24, "percent": 100}, {"hours": 2, "percent": 50}]}
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_reference(prefix: str = "CV") -> str:
    return prefix + "".join(secrets.choice(_ALPHABET) for _ in range(8))


def notify(db: Session, user_id: int, title: str, body: str = ""):
    db.add(Notification(user_id=user_id, title=title, body=body))


# ------------------------------------------------------------------ pricing
def price_food(db: Session, lines: list[dict]) -> tuple[int, list[dict]]:
    total, resolved = 0, []
    for line in lines or []:
        qty = int(line.get("quantity", 0))
        if qty < 1 or qty > 20:
            raise ApiError(400, "bad_quantity", "Food quantity must be between 1 and 20")
        item = db.get(FoodItem, line["item_id"])
        if not item or not item.is_available:
            raise ApiError(409, "food_unavailable", f"'{item.name if item else 'Item'}' is not available")
        if item.stock is not None and item.stock < qty:
            raise ApiError(409, "food_out_of_stock", f"Only {item.stock} left of '{item.name}'")
        unit, size = item.price, line.get("size")
        if size:
            match = next((s for s in (item.sizes or []) if s["name"] == size), None)
            if not match:
                raise ApiError(400, "bad_size", f"Unknown size '{size}' for {item.name}")
            unit += match["extra"]
        total += unit * qty
        resolved.append({"item": item, "size": size, "unit": unit, "qty": qty})
    return total, resolved


def validate_coupon(db: Session, code: str, user_id: int, show: Show, order_value: int, tickets_total: int) -> tuple[Coupon, int]:
    c = db.scalar(select(Coupon).where(Coupon.code == code.strip().upper()))
    now = utcnow()
    if not c or not c.is_active:
        raise ApiError(400, "coupon_invalid", "This coupon code is not valid")
    if c.expires_at and c.expires_at < now:
        raise ApiError(400, "coupon_expired", "This coupon has expired")
    if c.max_uses is not None and c.used_count >= c.max_uses:
        raise ApiError(400, "coupon_exhausted", "This coupon has reached its usage limit")
    if c.movie_id and c.movie_id != show.movie_id:
        raise ApiError(400, "coupon_not_applicable", "This coupon does not apply to this movie")
    if c.cinema_id and c.cinema_id != show.screen.cinema_id:
        raise ApiError(400, "coupon_not_applicable", "This coupon does not apply to this cinema")
    if order_value < c.min_order:
        raise ApiError(400, "coupon_min_order", f"Minimum order of Rs {c.min_order / 100:.0f} required")
    if db.scalar(select(CouponUsage.id).where(CouponUsage.coupon_id == c.id, CouponUsage.user_id == user_id)):
        raise ApiError(400, "coupon_used", "You have already used this coupon")
    disc = tickets_total * c.value // 100 if c.kind == "percent" else c.value
    if c.max_discount:
        disc = min(disc, c.max_discount)
    return c, max(0, min(disc, tickets_total))


def quote(db: Session, show: Show, seat_ids: list[int], food: list[dict], coupon_code: str | None, user_id: int) -> dict:
    cfg = get_settings()
    seats = db.scalars(select(Seat).where(Seat.id.in_(seat_ids), Seat.screen_id == show.screen_id)).all()
    if len(seats) != len(set(seat_ids)):
        raise ApiError(400, "invalid_seat", "Invalid seats")
    seat_lines = []
    for s in sorted(seats, key=lambda s: (s.grid_row, s.grid_col)):
        if s.category not in show.prices:
            raise ApiError(409, "seat_unpriced", f"Seat {s.label} has no price")
        seat_lines.append({"seat": s, "price": show.prices[s.category]})
    tickets_total = sum(l["price"] for l in seat_lines)
    food_total, food_lines = price_food(db, food)
    discount, coupon = 0, None
    if coupon_code:
        coupon, discount = validate_coupon(db, coupon_code, user_id, show, tickets_total + food_total, tickets_total)
    fee = cfg.convenience_fee_per_ticket * len(seat_lines)
    tax = round(cfg.tax_rate * (tickets_total - discount + food_total))
    total = tickets_total - discount + food_total + fee + tax
    return {"seat_lines": seat_lines, "food_lines": food_lines, "coupon": coupon, "tickets_total": tickets_total,
            "food_total": food_total, "discount": discount, "fee": fee, "tax": tax, "total": total}


def quote_public(q: dict) -> dict:
    return {
        "seats": [{"seat_id": l["seat"].id, "label": l["seat"].label, "category": l["seat"].category, "price": l["price"]}
                  for l in q["seat_lines"]],
        "food": [{"item_id": l["item"].id, "name": l["item"].name, "size": l["size"], "unit_price": l["unit"],
                  "quantity": l["qty"]} for l in q["food_lines"]],
        **{k: q[k] for k in ("tickets_total", "food_total", "discount", "fee", "tax", "total")},
        "coupon_code": q["coupon"].code if q["coupon"] else None,
    }


# ----------------------------------------------------------------- checkout
def checkout(db: Session, user_id: int, *, show_id: int, session_id: str, seat_ids: list[int],
             idempotency_key: str, food: list[dict], coupon_code: str | None, fulfilment: str,
             simulate_failure: bool = False) -> Booking:
    # 1. Idempotency: the same key returns the same booking, never a second one.
    prior = db.scalar(select(Booking).where(Booking.user_id == user_id, Booking.idempotency_key == idempotency_key))
    if prior:
        return prior

    show = get_bookable_show(db, show_id)
    seat_ids = list(dict.fromkeys(seat_ids))
    if not seat_ids:
        raise ApiError(400, "no_seats", "Select at least one seat")

    # 2. Validate lock ownership + expiry. FOR UPDATE stops the lock being reclaimed mid-checkout (PostgreSQL).
    locks = db.scalars(select(SeatLock).where(SeatLock.show_id == show_id, SeatLock.seat_id.in_(seat_ids))
                       .with_for_update()).all()
    by_seat = {l.seat_id: l for l in locks}
    now = utcnow()
    for sid in seat_ids:
        lock = by_seat.get(sid)
        if lock is None:
            db.rollback()
            raise ApiError(409, "lock_expired", "Your seat hold expired. Please select your seats again.", [sid])
        if lock.user_id != user_id or lock.session_id != session_id:
            db.rollback()
            raise ApiError(409, "lock_not_owned", "These seats are held by another session", [sid])
        if lock.expires_at <= now:
            cleanup_expired(db, show_id)
            db.commit()
            raise ApiError(409, "lock_expired", "Your seat hold expired. Please select your seats again.", [sid])

    # 3. Server-side price calculation; client totals are never accepted.
    q = quote(db, show, seat_ids, food, coupon_code, user_id)

    # 4. Payment (development simulator -- NOT a real gateway). Failure keeps the hold so the user can retry.
    if simulate_failure:
        db.add(Payment(user_id=user_id, provider="simulator", status="failed", amount=q["total"], idempotency_key=idempotency_key))
        db.commit()
        raise ApiError(402, "payment_failed", "Payment failed (simulated). Your seats are still held, please retry.")

    cinema = show.screen.cinema
    booking = Booking(
        reference=new_reference(), user_id=user_id, show_id=show_id, status="confirmed", payment_status="paid",
        idempotency_key=idempotency_key, tickets_total=q["tickets_total"], food_total=q["food_total"],
        discount=q["discount"], fee=q["fee"], tax=q["tax"], total=q["total"],
        coupon_code=q["coupon"].code if q["coupon"] else None,
        movie_title=show.movie.title, cinema_name=cinema.name, screen_name=show.screen.name,
        starts_at=show.starts_at, is_demo=False)
    for l in q["seat_lines"]:
        s = l["seat"]
        booking.seats.append(BookingSeat(show_id=show_id, seat_id=s.id, row_label=s.row_label,
                                         number_label=s.number_label, category=s.category, price=l["price"]))
    try:
        db.add(booking)
        db.flush()
        db.add(Payment(booking_id=booking.id, user_id=user_id, provider="simulator", status="succeeded",
                       amount=q["total"], idempotency_key=idempotency_key))
        if q["coupon"]:
            db.add(CouponUsage(coupon_id=q["coupon"].id, user_id=user_id, booking_id=booking.id))
            used = db.execute(update(Coupon).where(Coupon.id == q["coupon"].id,
                                                   (Coupon.max_uses.is_(None)) | (Coupon.used_count < Coupon.max_uses))
                              .values(used_count=Coupon.used_count + 1))
            if used.rowcount != 1:
                raise ApiError(400, "coupon_exhausted", "This coupon has reached its usage limit")
        if q["food_lines"]:
            _create_food_order(db, user_id, booking.id, q["food_lines"], fulfilment)
        for lock in locks:
            db.delete(lock)  # locks become confirmed seats only because this whole transaction succeeds
        notify(db, user_id, "Booking confirmed", f"{booking.movie_title} - {booking.reference}")
        db.commit()
    except IntegrityError:
        db.rollback()
        again = db.scalar(select(Booking).where(Booking.user_id == user_id, Booking.idempotency_key == idempotency_key))
        if again:  # a parallel request with the same key won
            return again
        raise ApiError(409, "seat_already_booked", "Seat already booked", seat_ids)
    except ApiError:
        db.rollback()
        raise
    return booking


def _create_food_order(db: Session, user_id: int, booking_id: int | None, lines: list[dict], fulfilment: str) -> FoodOrder:
    cfg = get_settings()
    subtotal = sum(l["unit"] * l["qty"] for l in lines)
    tax = round(cfg.tax_rate * subtotal) if booking_id is None else 0  # tax for booking food is on the booking
    order = FoodOrder(order_number=new_reference("FD"), user_id=user_id, booking_id=booking_id,
                      fulfilment=fulfilment, subtotal=subtotal, tax=tax, total=subtotal + tax, status="confirmed")
    for l in lines:
        res = db.execute(update(FoodItem).where(FoodItem.id == l["item"].id, FoodItem.is_available.is_(True),
                                                (FoodItem.stock.is_(None)) | (FoodItem.stock >= l["qty"]))
                         .values(stock=FoodItem.stock - l["qty"] if l["item"].stock is not None else FoodItem.stock))
        if res.rowcount != 1:
            raise ApiError(409, "food_out_of_stock", f"'{l['item'].name}' just ran out")
        order.items.append(FoodOrderItem(item_id=l["item"].id, name=l["item"].name, size=l["size"],
                                         unit_price=l["unit"], quantity=l["qty"]))
    db.add(order)
    return order


def place_food_order(db: Session, user_id: int, lines: list[dict], fulfilment: str) -> FoodOrder:
    if not lines:
        raise ApiError(400, "empty_order", "Your food cart is empty")
    _, resolved = price_food(db, lines)
    order = _create_food_order(db, user_id, None, resolved, fulfilment)
    notify(db, user_id, "Food order placed", order.order_number)
    db.commit()
    return order


# ------------------------------------------------------------- cancellation
def get_policy(db: Session) -> dict:
    row = db.get(Setting, "cancellation_policy")
    return row.value if row else DEFAULT_POLICY


def refund_percent(policy: dict, hours_before: float) -> int:
    for tier in sorted(policy["tiers"], key=lambda t: -t["hours"]):
        if hours_before >= tier["hours"]:
            return tier["percent"]
    return 0


def cancel_booking(db: Session, booking: Booking, *, by_admin: bool = False) -> Booking:
    if booking.status != "confirmed":
        raise ApiError(409, "not_cancellable", "This booking is already cancelled")
    now = utcnow()
    if booking.starts_at <= now:
        raise ApiError(409, "show_started", "Bookings cannot be cancelled after the show has started")
    if booking.checked_in_at:
        raise ApiError(409, "already_used", "This ticket has already been used")
    hours = (booking.starts_at - now).total_seconds() / 3600
    pct = 100 if by_admin else refund_percent(get_policy(db), hours)
    refundable = booking.total - booking.fee  # convenience fee is non-refundable (unless admin cancels)
    refund = booking.total if by_admin else refundable * pct // 100
    booking.status, booking.cancelled_at = "cancelled", now
    booking.refund_amount = refund
    booking.payment_status = "refunded" if refund >= booking.total else ("partially_refunded" if refund else "paid")
    for bs in booking.seats:
        bs.is_active = False  # frees the seats for the show (partial unique index only covers active rows)
    for order in db.scalars(select(FoodOrder).where(FoodOrder.booking_id == booking.id)):
        if order.status in ("pending", "confirmed"):
            order.status = "cancelled"
    db.add(Refund(booking_id=booking.id, amount=refund, reason=f"{pct}% refund policy" if not by_admin else "Cancelled by admin"))
    notify(db, booking.user_id, "Booking cancelled", f"{booking.reference}: refund Rs {refund / 100:.2f}")
    db.commit()
    return booking
