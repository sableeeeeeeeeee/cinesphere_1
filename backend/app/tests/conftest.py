import os
import tempfile
import uuid
from datetime import timedelta

# Must be set before the app is imported. Set TEST_DATABASE_URL to a PostgreSQL URL to run the suite on Postgres.
_tmp = os.path.join(tempfile.gettempdir(), f"cinesphere_test_{uuid.uuid4().hex}.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_tmp}")
os.environ["ENV"] = "dev"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import auth_limiter, create_access_token, hash_password  # noqa: E402
from app.db.session import Base, SessionLocal, engine, utcnow  # noqa: E402
from app.main import app  # noqa: E402
from app.models import FoodCategory, FoodItem, User  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    auth_limiter.reset()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


def make_user(email: str, password="Passw0rd!x", role="customer", name="Test User") -> int:
    with SessionLocal() as s:
        u = User(name=name, email=email, password_hash=hash_password(password), role=role)
        s.add(u)
        s.commit()
        return u.id


def login(client, email: str, password="Passw0rd!x") -> dict:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin_h(client):
    make_user("admin@t.example.com", role="admin", name="Admin")
    return login(client, "admin@t.example.com")


def new_customer(client, n: int) -> dict:
    """Mint a token directly (login is covered by the auth tests and is rate limited)."""
    uid = make_user(f"user{n}@t.example.com", name=f"User {n}")
    return {"Authorization": f"Bearer {create_access_token(uid, 'customer')}"}


@pytest.fixture
def world(client, admin_h):
    """A movie, a cinema, a 4x6 screen and a show tomorrow, all created through the admin API."""
    movie = client.post("/api/admin/movies", headers=admin_h, json={"title": "Test Movie", "genres": ["Drama"], "duration_min": 100}).json()
    cinema = client.post("/api/admin/cinemas", headers=admin_h, json={"name": "Test Cinema", "city": "Chennai"}).json()
    screen = client.post(f"/api/admin/cinemas/{cinema['id']}/screens", headers=admin_h, json={"name": "Audi 1", "rows": 4, "cols": 6}).json()
    start = (utcnow() + timedelta(days=1)).isoformat() + "Z"
    show = client.post("/api/admin/shows", headers=admin_h, json={
        "movie_id": movie["id"], "screen_id": screen["id"], "starts_at": start,
        "prices": {"standard": 10000, "premium": 20000}}).json()
    seats = client.get(f"/api/shows/{show['id']}/seats").json()["seats"]
    with SessionLocal() as s:
        cat = FoodCategory(name="Popcorn")
        s.add(cat)
        s.flush()
        s.add_all([FoodItem(category_id=cat.id, name="Popcorn", price=15000, sizes=[{"name": "Large", "extra": 5000}]),
                   FoodItem(category_id=cat.id, name="Sold Out", price=5000, is_available=False)])
        s.commit()
    return {"movie": movie, "cinema": cinema, "screen": screen, "show": show, "seats": sorted(seats, key=lambda s: s["id"])}
