# Deploying CineSphere (Render for backend + database, Vercel for frontend)

This guide has **not** been run against real Render/Vercel accounts, and the app has not been tested on PostgreSQL yet.
So do Step 0 first. Free-tier limits and menu names change, so check each provider's current pricing/UI if something differs.

How it fits together: the browser only talks to your **Vercel** site. Vercel forwards every `/api/...` request to the **Render** backend
(see `frontend/vercel.json`). To the browser it looks like one website, so login cookies work without extra CORS/cookie setup.

## Step 0: Test on PostgreSQL locally (strongly recommended)

Needs Docker Desktop running. In cmd, from the `movie-booking` folder:

```bat
docker compose up -d
cd backend
.venv\Scripts\activate.bat
copy ..\.env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --port 8000
```

In a second cmd window run the tests against Postgres (create the test database first):

```bat
docker compose exec db psql -U cinesphere -c "CREATE DATABASE cinesphere_test;"
cd backend
set TEST_DATABASE_URL=postgresql+psycopg2://cinesphere:cinesphere@localhost:5432/cinesphere_test
pytest -q
```

If all tests pass, the seat locking and double-booking protection also work on PostgreSQL. If any fail, send me the output before deploying.

## Step 1: Put the code on GitHub

Create an empty repository on github.com (private is fine), then in cmd from the `movie-booking` folder:

```bat
git init
git add .
git commit -m "CineSphere"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/cinesphere.git
git push -u origin main
```

`.gitignore` already keeps `.env`, databases and `node_modules` out. Never commit real secrets.

## Step 2: Database and backend on Render

1. Sign up at render.com with GitHub.
2. **New > PostgreSQL.** Name it `cinesphere-db`, pick a region near you, create it. Copy its **Internal Database URL** (or External if the backend is in a different region).
3. **New > Web Service**, connect your GitHub repo, then set:
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Under **Environment**, add:

| Key | Value |
|---|---|
| `PYTHON_VERSION` | `3.12.3` |
| `DATABASE_URL` | the database URL from step 2 (the `postgres://` form is fine, the app converts it) |
| `SECRET_KEY` | a long random string: run `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `ENV` | `prod` |
| `COOKIE_SECURE` | `true` |
| `CORS_ORIGINS` | your Vercel URL, e.g. `https://cinesphere.vercel.app` (add after Step 3) |
| `ADMIN_EMAIL` | the email you want for the admin account |
| `ADMIN_PASSWORD` | a **strong, private** password |
| `SEED_DEMO_ON_START` | `true` for the first deploy only (see below) |

5. Deploy. When it finishes, open `https://YOUR-BACKEND.onrender.com/api/health`. It should show `{"status":"ok"}`.
6. After the first successful start (demo data and your admin exist), change `SEED_DEMO_ON_START` to `false`. It only seeds an empty database, so leaving it on is harmless but unnecessary.

## Step 3: Frontend on Vercel

1. Open `frontend/vercel.json` and replace `YOUR-BACKEND.onrender.com` with your real Render hostname. Commit and push.
2. Sign up at vercel.com with GitHub, **Add New > Project**, import the repo, then set:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite
   - **Build Command:** `npm run build`, **Output Directory:** `dist`
3. Deploy. Put the resulting URL into Render's `CORS_ORIGINS` (Step 2.4) and let Render redeploy.
4. Open the Vercel URL, log in with your `ADMIN_EMAIL` / `ADMIN_PASSWORD`.

## Step 4: Before you share the link

- The seed also creates **demo accounts with publicly known passwords** (`demo@...` / `Demo@12345`, `staff@...` / `Staff@12345`, and four sample customers). In Admin > Users, suspend those you do not need.
- Forgot-password does not work in production: it needs an email (SMTP) integration that is not built yet.
- Payments are still a simulator. Do not present this as a real payment system.
- Free hosting usually sleeps after inactivity, so the first request can take around a minute. Free databases often have limits or expiry, so check the provider's current terms before relying on the data.
- The login rate limiter is per process. That is fine for one small server.

## Updating later

Push to `main` on GitHub. Render and Vercel redeploy automatically. Database changes need a new Alembic migration
(`alembic revision --autogenerate -m "describe change"`), which runs on start through the Start Command above.
