# CineSphere: movie ticket booking (React + FastAPI + PostgreSQL)

Customer site (browse, trailers, seat map, checkout, food, reviews, tickets with QR) and an admin panel
(dashboard, movies, cinemas, **visual seat-layout editor**, shows, bookings, food, reviews, users, coupons, audit log, ticket validation).

## What was and was not verified

| Verified in the build environment | NOT verified (please check on your machine) |
|---|---|
| 23 backend tests pass on **SQLite**, including 20-way concurrent lock test, concurrent checkout, duplicate-checkout and DB-constraint tests | Running on **PostgreSQL** (code is written for it, but no Postgres was available here) |
| Seed script, Alembic migration (applied to SQLite), live HTTP smoke test of the seeded API | Redis (not used: see "Remaining work") |
| Frontend production build (`vite build`) succeeds | The UI was **never opened in a browser** here, so expect small visual/runtime bugs to fix |

**Deploying online:** see `DEPLOY.md`.

## 1. Prerequisites (Windows)

Install: **Python 3.11+** (tick "Add to PATH"), **Node.js 20+**, **Git**, and optionally **Docker Desktop** (for PostgreSQL). VS Code is fine as the editor.
Run every command below in a **PowerShell** terminal (VS Code: Terminal > New Terminal).

## 2. Backend

```powershell
cd movie-booking\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
copy ..\.env.example .env             # then edit .env (see below)
```

**Option A: quickest (SQLite, no Docker).** In `.env` set `DATABASE_URL=sqlite:///./cinesphere.db` and skip to the seed step.

**Option B: PostgreSQL (recommended, the real target).** From the `movie-booking` folder:

```powershell
docker compose up -d                  # starts PostgreSQL (and Redis, currently unused)
```

Keep `DATABASE_URL=postgresql+psycopg2://cinesphere:cinesphere@localhost:5432/cinesphere` in `.env`, then in `backend`:

```powershell
alembic upgrade head                  # creates the tables (SQLite creates them automatically on startup)
```

Seed demo data and start the API (still in `backend`, venv active):

```powershell
python -m app.seed                    # add  --reset  to wipe everything and re-seed (development only!)
uvicorn app.main:app --reload --port 8000
```

API docs (Swagger): http://localhost:8000/docs

Generate a real secret before sharing the app: `python -c "import secrets;print(secrets.token_urlsafe(48))"` and put it in `SECRET_KEY`.

## 3. Frontend

Second PowerShell window:

```powershell
cd movie-booking\frontend
npm install
npm run dev
```

Open http://localhost:5173 (the dev server proxies `/api` to port 8000).

## 4. Accounts (development only, created by the seed script)

| Role | Email | Password |
|---|---|---|
| Admin | `admin@cinesphere.example.com` | `Admin@12345` |
| Customer | `demo@cinesphere.example.com` | `Demo@12345` |
| Counter staff | `staff@cinesphere.example.com` | `Staff@12345` |

Change them via `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env` *before* seeding. Registration always creates customers; only an existing admin can promote users (Admin > Users).

## 5. Try it

**Create a cinema, screen, layout and show (Admin)**
1. Sign in as admin > **Cinemas & screens** > *New cinema*, then *+ Screen* (rows/columns give a starter grid).
2. Click **Layout**. Click seats to select, then apply a category, *Make empty / aisle*, or *Toggle disabled*. Click a row letter box to rename it; double-click it to select the row. Use +/- to add or remove rows and columns. Save.
3. **Showtimes** > *Add show*: pick movie, screen, local start time, and a price for each seat category on that screen. Overlaps and past times are rejected.

**Test seat locking with two people:** open one normal window signed in as `demo@...` and one **incognito** window signed in as another customer (register one). Open the same show's seat page in both. Select a seat in window 1: within ~3 seconds it shows as "Held by someone" in window 2, and window 2 cannot take it. Let the timer run out (5 minutes, `SEAT_LOCK_SECONDS`) or deselect and it frees up. Two tabs of the *same* account count as separate sessions too.

**Complete a demo booking:** Movie > pick date and showtime > select seats > *Continue to checkout* > add food, try coupon `WELCOME10` or `FLAT50` > *Pay* (simulator; tick "Simulate a payment failure" to see the retry path, the hold is kept) > ticket page with QR. Staff can validate it under **Admin > Validate ticket** (type the reference).

## 6. Tests

```powershell
cd movie-booking\backend
.\.venv\Scripts\Activate.ps1
pytest -q
```

Uses a temporary SQLite file. To run the same suite on PostgreSQL (recommended, since this is where row-level behaviour matters):
`$env:TEST_DATABASE_URL="postgresql+psycopg2://cinesphere:cinesphere@localhost:5432/cinesphere_test"; pytest -q` (create the `cinesphere_test` database first; the tests drop and recreate its tables).

## 7. How double booking is prevented

1. `seat_locks` has `UNIQUE(show_id, seat_id)`. Locking inserts rows, so of N simultaneous requests the database lets exactly one in. Expired rows are deleted first, and also ignored by every read (`expires_at > now`), so correctness never depends on a cleanup job.
2. Checkout re-validates, inside one transaction, that every seat has a lock owned by *this user and this browser session* that has not expired (`SELECT ... FOR UPDATE` on PostgreSQL), recomputes the price on the server, then inserts `booking_seats` and deletes the locks together.
3. `booking_seats` has a partial unique index on `(show_id, seat_id) WHERE is_active`. Even if everything above were bypassed, the database refuses a second confirmed booking for the same seat (`test_database_itself_rejects_duplicate_confirmed_seat`). Cancelling sets `is_active=false`, freeing the seat while keeping history.
4. `UNIQUE(user_id, idempotency_key)` on bookings makes repeated or parallel checkout calls return the same booking.

## 8. Images (posters, backdrops, food)

The demo artwork is **original illustrated SVG art** generated by `tools/generate_assets.py` (no copyright issues). It is not photography.
To use real photos: save the file in `frontend/public/` (for example `frontend/public/images/food/popcorn.jpg`), then in the admin panel set the **Image URL** to `/images/food/popcorn.jpg`
(Admin > Food for food, Admin > Movies for poster and backdrop). Only use images you own or have a licence for.
Regenerate the demo artwork any time with `python tools/generate_assets.py`.

## 9. Project layout

```
backend/app/  api/ (routers)  models/  services/ (layout, locking, booking)  core/ (config, security)  db/  tests/  seed.py
backend/alembic/                      migrations
frontend/src/ pages/ components/ layouts/ context/ hooks/ services/ utils/
```

Money is stored as integer paise. Datetimes are stored in UTC and shown in the browser's local time.

## 10. Implemented

Auth (register/login/logout, JWT access token in memory + rotating httpOnly refresh cookie, forgot/reset password, profile, change password, roles customer/staff/admin, login rate limit), movie discovery (search, filters, sort, pagination, trending/top-rated, recently viewed, similar), movie page with embedded trailer, showtimes by city/date, reviews (ratings, edit/delete, helpful votes, reports, moderation, server-side *Verified booking* = confirmed booking for a show that has already started), cinemas/screens/layout editor with safe edits, shows with overlap/past checks, seat map with live polling and countdown, server-side locking, checkout with server-side pricing/coupons/idempotency/simulated payment, cancellation with admin-configurable refund tiers (API: `PUT /api/admin/cancellation-policy`), QR ticket + print, food ordering (menu, sizes, stock, standalone and with booking, status workflow), watchlist, in-app notifications, coupons, admin dashboard (cards + 5 charts from DB, filters), admin modules, audit log, QR/reference validation for staff, demo seed.

## 11. Remaining work / known limitations

- **Redis is not used.** Locks live in the database, which is the final authority anyway. Redis could be added as a fast first-pass cache.
- Seat updates use **polling every 3 s**, not WebSockets.
- No real payment gateway or email sending: payments are a labelled simulator; the reset token is returned by the API only when `ENV=dev`; notification emails/SMTP are not implemented. Release-reminder and "lock about to expire" notifications are not implemented.
- The rate limiter is per-process (use Redis or a proxy with several workers). CSRF: the refresh cookie is `SameSite=Lax` and used only by `/auth/refresh`; no separate CSRF token.
- QR validation is by typed/scanned reference text; there is no camera scanner. "Download ticket" is browser print/save-as-PDF.
- Admin UI gaps: no UI for the cancellation policy (API only), no review-moderation history page (actions appear in the audit log), poster images are URLs only (no upload), food categories are created implicitly by name, dynamic pricing is per show and seat category only (no time-based rules).
- Recommendations are genre-based ("similar movies") and recently viewed; they do not use favourites yet.
- Layout editor has no undo and uses click selection (no drag). Not tested with screen readers.
- Seed posters and food pictures are generated illustrations, not photographs; the demo trailer is the Creative Commons "Big Buck Bunny". Replace via the admin panel.
