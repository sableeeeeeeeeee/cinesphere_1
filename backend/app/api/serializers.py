"""Plain-dict serializers. Datetimes are UTC and sent with a trailing Z."""
from app.models import Booking, Cinema, FoodItem, FoodOrder, Movie, Review, Screen, Show, User


def iso(dt):
    return dt.isoformat() + "Z" if dt else None


def user_out(u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "phone": u.phone, "role": u.role, "is_active": u.is_active,
            "created_at": iso(u.created_at)}


def movie_out(m: Movie) -> dict:
    return {"id": m.id, "title": m.title, "synopsis": m.synopsis, "poster_url": m.poster_url,
            "backdrop_url": m.backdrop_url, "trailer_url": m.trailer_url, "director": m.director,
            "cast": m.cast or [], "language": m.language, "duration_min": m.duration_min,
            "certificate": m.certificate, "release_date": m.release_date.isoformat() if m.release_date else None,
            "status": m.status, "avg_rating": round(m.avg_rating or 0, 1), "rating_count": m.rating_count,
            "genres": [g.name for g in m.genres]}


def screen_out(s: Screen, with_layout: bool = False) -> dict:
    d = {"id": s.id, "cinema_id": s.cinema_id, "name": s.name, "label": s.label, "formats": s.formats,
         "layout_version": s.layout_version}
    if with_layout:
        d["layout"] = s.layout
    return d


def cinema_out(c: Cinema, with_screens: bool = False) -> dict:
    d = {"id": c.id, "name": c.name, "city": c.city, "address": c.address, "phone": c.phone,
         "amenities": c.amenities or [], "is_active": c.is_active}
    if with_screens:
        d["screens"] = [screen_out(s) for s in c.screens]
    return d


def show_out(s: Show, available: int | None = None, total: int | None = None) -> dict:
    d = {"id": s.id, "movie_id": s.movie_id, "movie_title": s.movie.title, "poster_url": s.movie.poster_url,
         "screen_id": s.screen_id, "screen_name": s.screen.name, "cinema_id": s.screen.cinema_id,
         "cinema_name": s.screen.cinema.name, "city": s.screen.cinema.city,
         "starts_at": iso(s.starts_at), "ends_at": iso(s.ends_at), "format": s.format, "language": s.language,
         "status": s.status, "prices": s.prices}
    if available is not None:
        d["available_seats"], d["total_seats"] = available, total
    return d


def booking_out(b: Booking) -> dict:
    return {"id": b.id, "reference": b.reference, "status": b.status, "payment_status": b.payment_status,
            "show_id": b.show_id, "movie_title": b.movie_title, "cinema_name": b.cinema_name,
            "screen_name": b.screen_name, "starts_at": iso(b.starts_at), "poster_url": b.show.movie.poster_url if b.show else None,
            "seats": [{"label": s.label, "category": s.category, "price": s.price} for s in b.seats],
            "tickets_total": b.tickets_total, "food_total": b.food_total, "discount": b.discount, "fee": b.fee,
            "tax": b.tax, "total": b.total, "coupon_code": b.coupon_code, "refund_amount": b.refund_amount,
            "checked_in_at": iso(b.checked_in_at), "created_at": iso(b.created_at)}


def food_item_out(f: FoodItem) -> dict:
    return {"id": f.id, "category_id": f.category_id, "category": f.category.name, "name": f.name,
            "description": f.description, "image_url": f.image_url, "price": f.price, "sizes": f.sizes or [],
            "is_available": f.is_available and (f.stock is None or f.stock > 0), "stock": f.stock}


def food_order_out(o: FoodOrder) -> dict:
    return {"id": o.id, "order_number": o.order_number, "status": o.status, "fulfilment": o.fulfilment,
            "booking_id": o.booking_id, "subtotal": o.subtotal, "tax": o.tax, "total": o.total,
            "created_at": iso(o.created_at),
            "items": [{"name": i.name, "size": i.size, "unit_price": i.unit_price, "quantity": i.quantity} for i in o.items]}


def review_out(r: Review, verified: bool, mine: bool = False) -> dict:
    return {"id": r.id, "movie_id": r.movie_id, "user_name": r.user.name, "rating": r.rating, "text": r.text,
            "helpful_count": r.helpful_count, "verified_booking": verified, "is_mine": mine,
            "created_at": iso(r.created_at), "updated_at": iso(r.updated_at)}
