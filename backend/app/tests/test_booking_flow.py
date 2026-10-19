import threading
import uuid
from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal, utcnow
from app.models import BookingSeat, Booking, Coupon, SeatLock, Show
from app.services import booking as booking_svc
from app.tests.conftest import login, make_user, new_customer


def lock(client, h, show_id, seat_ids, session="sess-aaaaaaaa"):
    return client.post(f"/api/shows/{show_id}/locks", headers=h, json={"seat_ids": seat_ids, "session_id": session})


def pay(client, h, show_id, seat_ids, session="sess-aaaaaaaa", key=None, **extra):
    body = {"show_id": show_id, "session_id": session, "seat_ids": seat_ids, "idempotency_key": key or uuid.uuid4().hex, **extra}
    return client.post("/api/bookings/checkout", headers=h, json=body)


# ------------------------------------------------------------------ auth
def test_register_login_me_and_no_self_promotion(client):
    r = client.post("/api/auth/register", json={"name": "Eve", "email": "eve@t.example.com", "password": "Passw0rd!x", "role": "admin"})
    assert r.status_code == 201
    assert r.json()["user"]["role"] == "customer"  # role in the body is ignored
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=h).json()["email"] == "eve@t.example.com"
    assert client.post("/api/auth/register", json={"name": "Eve", "email": "EVE@t.example.com", "password": "Passw0rd!x"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "eve@t.example.com", "password": "wrong-password"}).status_code == 401
    assert client.get("/api/admin/stats", headers=h).status_code == 403
    assert client.get("/api/admin/stats").status_code == 401


def test_refresh_cookie_session_and_password_reset(client):
    client.post("/api/auth/register", json={"name": "Sam", "email": "sam@t.example.com", "password": "Passw0rd!x"})
    assert client.post("/api/auth/refresh").status_code == 200  # cookie persisted "after page refresh"
    tok = client.post("/api/auth/forgot-password", json={"email": "sam@t.example.com"}).json()["dev_reset_token"]
    assert client.post("/api/auth/reset-password", json={"token": tok, "new_password": "NewPassw0rd!"}).status_code == 204
    assert client.post("/api/auth/reset-password", json={"token": tok, "new_password": "Another1234!"}).status_code == 400  # single use
    assert client.post("/api/auth/login", json={"email": "sam@t.example.com", "password": "NewPassw0rd!"}).status_code == 200


# ---------------------------------------------------------------- layout
def test_layout_validation_and_edit(client, admin_h, world):
    sid = world["screen"]["id"]
    layout = client.get(f"/api/admin/screens/{sid}", headers=admin_h).json()["layout"]
    bad = {**layout, "cells": layout["cells"][:-1]}
    assert client.put(f"/api/admin/screens/{sid}/layout", headers=admin_h, json=bad).status_code == 422
    dup = {**layout, "cells": [list(r) for r in layout["cells"]]}
    dup["cells"][0][1] = {"n": "1", "c": "standard", "d": False}
    assert client.put(f"/api/admin/screens/{sid}/layout", headers=admin_h, json=dup).status_code == 422

    ok = {**layout, "cells": [list(r) for r in layout["cells"]]}
    ok["cells"][0][2] = None  # aisle
    r = client.put(f"/api/admin/screens/{sid}/layout", headers=admin_h, json=ok)
    assert r.status_code == 200 and r.json()["summary"]["total_seats"] == 23
    # the customer map reflects the saved layout, not a hardcoded grid
    seats = client.get(f"/api/shows/{world['show']['id']}/seats").json()["seats"]
    assert len(seats) == 23


def test_layout_change_blocked_when_seat_is_booked(client, admin_h, world):
    u = new_customer(client, 1)
    seat = world["seats"][0]
    assert lock(client, u, world["show"]["id"], [seat["id"]]).status_code == 201
    assert pay(client, u, world["show"]["id"], [seat["id"]]).status_code == 201
    sid = world["screen"]["id"]
    layout = client.get(f"/api/admin/screens/{sid}", headers=admin_h).json()["layout"]
    layout["cells"][seat["grid_row"]][seat["grid_col"]] = None
    r = client.put(f"/api/admin/screens/{sid}/layout", headers=admin_h, json=layout)
    assert r.status_code == 422 and "cannot be removed" in str(r.json())


# ---------------------------------------------------------------- locking
def test_two_users_same_seat_and_release(client, world):
    a, b = new_customer(client, 1), new_customer(client, 2)
    show, seat = world["show"]["id"], world["seats"][0]["id"]
    assert lock(client, a, show, [seat]).status_code == 201
    r = lock(client, b, show, [seat], session="sess-bbbbbbbb")
    assert r.status_code == 409 and r.json()["code"] == "seat_already_locked"
    # same user in another browser tab is a different session
    assert lock(client, a, show, [seat], session="sess-othertab").status_code == 409
    states = {s["id"]: s["status"] for s in client.get(f"/api/shows/{show}/seats", headers=b, params={"session_id": "sess-bbbbbbbb"}).json()["seats"]}
    assert states[seat] == "locked"
    assert client.delete(f"/api/shows/{show}/locks", headers=a, params={"session_id": "sess-aaaaaaaa"}).status_code == 200
    assert lock(client, b, show, [seat], session="sess-bbbbbbbb").status_code == 201


def test_lock_expiry_frees_seat_and_blocks_checkout(client, world):
    a, b = new_customer(client, 1), new_customer(client, 2)
    show, seat = world["show"]["id"], world["seats"][1]["id"]
    assert lock(client, a, show, [seat]).status_code == 201
    with SessionLocal() as s:  # simulate five minutes passing
        for l in s.query(SeatLock).all():
            l.expires_at = utcnow() - timedelta(seconds=1)
        s.commit()
    r = pay(client, a, show, [seat])
    assert r.status_code == 409 and r.json()["code"] == "lock_expired"
    assert lock(client, b, show, [seat], session="sess-bbbbbbbb").status_code == 201


def test_cannot_checkout_seat_held_by_someone_else(client, world):
    a, b = new_customer(client, 1), new_customer(client, 2)
    show, seat = world["show"]["id"], world["seats"][2]["id"]
    lock(client, a, show, [seat])
    r = pay(client, b, show, [seat], session="sess-bbbbbbbb")
    assert r.status_code == 409 and r.json()["code"] in ("lock_not_owned", "lock_expired")


def test_past_show_cannot_be_locked(client, world):
    a = new_customer(client, 1)
    with SessionLocal() as s:
        sh = s.get(Show, world["show"]["id"])
        sh.starts_at = utcnow() - timedelta(minutes=5)
        s.commit()
    assert lock(client, a, world["show"]["id"], [world["seats"][0]["id"]]).json()["code"] == "show_started"


# --------------------------------------------------------------- checkout
def test_checkout_prices_are_server_side_and_idempotent(client, world):
    u = new_customer(client, 1)
    show = world["show"]["id"]
    seats = [world["seats"][0]["id"], world["seats"][1]["id"]]
    lock(client, u, show, seats)
    key = uuid.uuid4().hex
    r1 = pay(client, u, show, seats, key=key, food=[{"item_id": 1, "quantity": 2, "size": "Large"}], total=1)  # bogus total ignored
    assert r1.status_code == 201, r1.text
    b = r1.json()
    # tickets 2x100 + food 2x(150+50) = 600; fee 2x20; tax 18% of 600 = 108; total 748
    assert (b["tickets_total"], b["food_total"], b["fee"], b["tax"], b["total"]) == (20000, 40000, 4000, 10800, 74800)
    r2 = pay(client, u, show, seats, key=key)  # retry with same key
    assert r2.status_code == 201 and r2.json()["id"] == b["id"]
    with SessionLocal() as s:
        assert s.query(Booking).count() == 1 and s.query(BookingSeat).count() == 2
    assert client.get("/api/bookings/my", headers=u).json()["upcoming"][0]["reference"] == b["reference"]
    assert len(client.get("/api/food/orders/my", headers=u).json()) == 1


def test_payment_failure_keeps_hold_and_retry_succeeds(client, world):
    u = new_customer(client, 1)
    show, seat = world["show"]["id"], world["seats"][0]["id"]
    lock(client, u, show, [seat])
    r = pay(client, u, show, [seat], simulate_failure=True)
    assert r.status_code == 402 and r.json()["code"] == "payment_failed"
    with SessionLocal() as s:
        assert s.query(Booking).count() == 0 and s.query(SeatLock).count() == 1
    assert pay(client, u, show, [seat]).status_code == 201


def test_booked_seat_cannot_be_locked_again(client, world):
    a, b = new_customer(client, 1), new_customer(client, 2)
    show, seat = world["show"]["id"], world["seats"][0]["id"]
    lock(client, a, show, [seat])
    pay(client, a, show, [seat])
    r = lock(client, b, show, [seat], session="sess-bbbbbbbb")
    assert r.status_code == 409 and r.json()["code"] == "seat_already_booked"


def test_unavailable_food_rejected(client, world):
    u = new_customer(client, 1)
    show, seat = world["show"]["id"], world["seats"][0]["id"]
    lock(client, u, show, [seat])
    r = pay(client, u, show, [seat], food=[{"item_id": 2, "quantity": 1}])
    assert r.status_code == 409 and r.json()["code"] == "food_unavailable"
    assert client.post("/api/food/orders", headers=u, json={"items": [{"item_id": 2, "quantity": 1}]}).status_code == 409
    o = client.post("/api/food/orders", headers=u, json={"items": [{"item_id": 1, "quantity": 1}]}).json()
    assert o["subtotal"] == 15000 and o["tax"] == 2700 and o["total"] == 17700


# ----------------------------------------------------------- cancellation
@pytest.mark.parametrize("hours,expected_pct", [(30, 100), (5, 50), (1, 0)])
def test_cancellation_refund_policy(client, world, hours, expected_pct):
    u = new_customer(client, 1)
    show, seat = world["show"]["id"], world["seats"][0]["id"]
    lock(client, u, show, [seat])
    b = pay(client, u, show, [seat]).json()
    with SessionLocal() as s:
        s.get(Show, show).starts_at = utcnow() + timedelta(hours=hours)
        s.get(Booking, b["id"]).starts_at = utcnow() + timedelta(hours=hours)
        s.commit()
    r = client.post(f"/api/bookings/{b['id']}/cancel", headers=u)
    assert r.status_code == 200, r.text
    assert r.json()["refund_amount"] == (b["total"] - b["fee"]) * expected_pct // 100
    assert client.post(f"/api/bookings/{b['id']}/cancel", headers=u).status_code == 409
    # the seat is free again
    v = new_customer(client, 2)
    assert lock(client, v, show, [seat], session="sess-bbbbbbbb").status_code == 201


# ----------------------------------------------------------------- coupons
def test_coupon_rules(client, world):
    u = new_customer(client, 1)
    show, seats = world["show"]["id"], [world["seats"][0]["id"], world["seats"][1]["id"]]
    with SessionLocal() as s:
        s.add_all([Coupon(code="TEN", kind="percent", value=10), Coupon(code="OLD", kind="percent", value=10, expires_at=utcnow() - timedelta(days=1)),
                   Coupon(code="BIG", kind="fixed", value=1000, min_order=999999)])
        s.commit()
    lock(client, u, show, seats)
    q = lambda code: client.post(f"/api/shows/{show}/quote", headers=u, json={"seat_ids": seats, "coupon_code": code})
    assert q("TEN").json()["discount"] == 2000
    assert q("OLD").json()["code"] == "coupon_expired"
    assert q("BIG").json()["code"] == "coupon_min_order"
    assert q("NOPE").json()["code"] == "coupon_invalid"
    assert pay(client, u, show, seats, coupon_code="TEN").status_code == 201
    assert q("TEN").json()["code"] == "coupon_used"  # one use per customer


# ----------------------------------------------------------------- reviews
def test_reviews_verified_label_and_duplicates(client, world):
    u, v = new_customer(client, 1), new_customer(client, 2)
    show, seat, mid = world["show"]["id"], world["seats"][0]["id"], world["movie"]["id"]
    lock(client, u, show, [seat])
    pay(client, u, show, [seat])
    assert client.post(f"/api/movies/{mid}/reviews", headers=u, json={"rating": 5, "text": "Loved it"}).status_code == 201
    assert client.post(f"/api/movies/{mid}/reviews", headers=u, json={"rating": 4}).status_code == 409
    assert client.post(f"/api/movies/{mid}/reviews", headers=v, json={"rating": 3, "text": "Ok"}).status_code == 201
    assert client.post(f"/api/movies/{mid}/reviews", headers=v, json={"rating": 9}).status_code == 422
    data = client.get(f"/api/movies/{mid}/reviews").json()
    # nobody is verified yet: the show has not started
    assert not any(r["verified_booking"] for r in data["items"])
    with SessionLocal() as s:
        s.get(Show, show).starts_at = utcnow() - timedelta(hours=3)
        s.commit()
    data = client.get(f"/api/movies/{mid}/reviews").json()
    flags = {r["user_name"]: r["verified_booking"] for r in data["items"]}
    assert sorted(flags.values()) == [False, True]
    assert data["avg_rating"] == 4.0 and data["total"] == 2
    rid = next(r["id"] for r in data["items"] if r["verified_booking"])
    assert client.patch(f"/api/reviews/{rid}", headers=v, json={"rating": 1}).status_code == 404  # not the author


# ------------------------------------------------------------------- admin
def test_show_overlap_rejected_and_stats_from_db(client, admin_h, world):
    start = world["show"]["starts_at"]
    r = client.post("/api/admin/shows", headers=admin_h, json={"movie_id": world["movie"]["id"], "screen_id": world["screen"]["id"],
                                                               "starts_at": start, "prices": {"standard": 1, "premium": 1}})
    assert r.status_code == 409
    past = client.post("/api/admin/shows", headers=admin_h, json={"movie_id": world["movie"]["id"], "screen_id": world["screen"]["id"],
                                                                  "starts_at": (utcnow() - timedelta(days=1)).isoformat() + "Z", "prices": {"standard": 1, "premium": 1}})
    assert past.status_code == 422
    u = new_customer(client, 1)
    show, seat = world["show"]["id"], world["seats"][0]["id"]
    lock(client, u, show, [seat])
    b = pay(client, u, show, [seat]).json()
    cards = client.get("/api/admin/stats", headers=admin_h).json()["cards"]
    assert cards["confirmed_revenue"] == b["total"] and cards["tickets_sold"] == 1
    client.post(f"/api/admin/bookings/{b['id']}/cancel", headers=admin_h)
    cards = client.get("/api/admin/stats", headers=admin_h).json()["cards"]
    assert cards["confirmed_revenue"] == 0 and cards["gross_bookings_value"] == b["total"] and cards["refunds"] == b["total"]
    assert any(a["action"] == "booking.cancel" for a in client.get("/api/admin/audit-logs", headers=admin_h).json())


def test_suspended_user_cannot_use_token(client, admin_h):
    uid = make_user("sus@t.example.com")
    h = login(client, "sus@t.example.com")
    client.patch(f"/api/admin/users/{uid}", headers=admin_h, json={"is_active": False})
    assert client.get("/api/auth/me", headers=h).status_code == 401


# ------------------------------------------------------------- concurrency
def test_concurrent_lock_requests_only_one_wins(client, world):
    """20 customers hit the same seat at the same instant. Exactly one may hold it."""
    show, seat = world["show"]["id"], world["seats"][0]["id"]
    headers = [new_customer(client, i) for i in range(20)]
    barrier, results = threading.Barrier(20), []

    def worker(i):
        barrier.wait()
        results.append(lock(client, headers[i], show, [seat], session=f"sess-worker-{i:03d}").status_code)

    ts = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(results).count(201) == 1 and results.count(409) == 19
    with SessionLocal() as s:
        assert s.query(SeatLock).count() == 1


def test_concurrent_checkout_same_seat_never_double_books(client, world):
    """Worst case: two customers both hold the seat because the first lock expired and was re-taken.
    Even if both reach checkout, the database allows only one confirmed booking for the seat."""
    show, seat = world["show"]["id"], world["seats"][0]["id"]
    a, b = new_customer(client, 1), new_customer(client, 2)
    barrier, results = threading.Barrier(2), []

    def worker(h, sess):
        lock(client, h, show, [seat], session=sess)
        barrier.wait()
        results.append(pay(client, h, show, [seat], session=sess).status_code)

    ts = [threading.Thread(target=worker, args=(a, "sess-aaaaaaaa")), threading.Thread(target=worker, args=(b, "sess-bbbbbbbb"))]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert results.count(201) == 1
    with SessionLocal() as s:
        assert s.query(BookingSeat).filter(BookingSeat.seat_id == seat, BookingSeat.is_active.is_(True)).count() == 1


def test_database_itself_rejects_duplicate_confirmed_seat(client, world):
    """The final authority: bypass all application logic and try to insert a second active row."""
    u = new_customer(client, 1)
    show, seat = world["show"]["id"], world["seats"][0]["id"]
    lock(client, u, show, [seat])
    b = pay(client, u, show, [seat]).json()
    with SessionLocal() as s:
        s.add(BookingSeat(booking_id=b["id"], show_id=show, seat_id=seat, row_label="A", number_label="1", category="standard", price=1))
        with pytest.raises(IntegrityError):
            s.commit()


def test_same_idempotency_key_in_parallel_makes_one_booking(client, world):
    u = new_customer(client, 1)
    show, seat = world["show"]["id"], world["seats"][0]["id"]
    lock(client, u, show, [seat])
    barrier, out = threading.Barrier(4), []

    def worker():
        barrier.wait()
        out.append(pay(client, u, show, [seat], key="same-key-12345678"))

    ts = [threading.Thread(target=worker) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert {r.status_code for r in out} <= {201, 409}
    assert len({r.json()["id"] for r in out if r.status_code == 201}) == 1
    with SessionLocal() as s:
        assert s.query(Booking).count() == 1


def test_dashboard_updates_after_booking_and_respects_timezone(client, admin_h, world):
    before = client.get("/api/admin/stats", headers=admin_h, params={"tz": 330}).json()["cards"]
    assert before["tickets_sold"] == 0 and before["confirmed_revenue"] == 0
    u = new_customer(client, 1)
    show, seats = world["show"]["id"], [world["seats"][0]["id"], world["seats"][1]["id"]]
    lock(client, u, show, seats)
    b = pay(client, u, show, seats).json()
    for tz in (-720, -300, 0, 330, 720):  # whatever zone the admin is in, today's booking is counted
        s = client.get("/api/admin/stats", headers=admin_h, params={"tz": tz}).json()
        assert s["cards"]["confirmed_revenue"] == b["total"] and s["cards"]["tickets_sold"] == 2, tz
        assert sum(d["revenue"] for d in s["daily"]) == b["total"]
        assert s["popular_movies"][0]["tickets"] == 2
        assert s["revenue_by_cinema"][0]["revenue"] == b["total"]
