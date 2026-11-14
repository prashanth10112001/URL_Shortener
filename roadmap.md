# URL Shortener + Rate Limiter: Phases and Steps

Stack: Python 3.12, FastAPI, PostgreSQL, Redis, React, Docker, Nginx.
Rule: commit to Git at the end of every phase. Ask for the explanation or code of any step when you need it.
Windows note: if a package is blocked ("Application Control policy"), install it in pure-Python mode or tell me and we pick a substitute.

---

## Phase 0: Setup (DONE)

1. Install Python, Git, Docker Desktop, editor.
2. Create project folder, Git repo, `backend` folder.
3. Create virtual environment.
4. Install FastAPI, Uvicorn, python-dotenv.
5. Docker Compose with PostgreSQL and Redis; settings in `.env`; `.gitignore` excludes `.env` and venv.
6. One route: health check.
7. Run server, test in browser and `/docs`.
8. Commit.

## Phase 1: Core shortener

1. Install SQLAlchemy, psycopg, Alembic.
2. Load settings (database address, base URL) from `.env` in one place.
3. Create engine (connection pool) and a per-request session helper.
4. Define `urls` model: id (sequence), code (unique), long_url, created_at, expires_at, is_active, click_count.
5. Set up Alembic; generate first migration; read it before running.
6. Run migration; confirm table and sequence exist.
7. Write Base62 encoder with 62^6 offset. Check: 1204567 gives `10053MV`.
8. Write request and response schemas (camelCase in JSON).
9. Shortener logic: next sequence number, encode, insert, commit, build short URL.
10. Route `POST /api/shorten` (201).
11. Route `GET /{code}` (404 unknown, else 302). Register it last.
12. Test the encoder (1204567 gives `10053MV`, next gives `10053MW`).
13. Try end to end in `/docs` and browser; check the row in the database.
14. Commit.

Done when: test passes, short link redirects, unknown code gives 404, row visible in database.

## Phase 2: Validation, aliases, expiry

1. URL rules: http or https only, max 2048 chars, host present, no username/password in URL, not our own domain.
2. Alias rules: 4 to 30 chars of letters, digits, `-`, `_`; reserved words list (api, links, login, register, api-keys, docs, health).
3. Expiry rule: must be in the future.
4. Custom error types and one central handler returning detail, code, and optional field.
5. Update shortener: use alias if given; rely on the unique constraint (409 if taken); for generated codes retry up to 3 times on collision.
6. Update redirect: 404 unknown, 410 expired or disabled.
7. Tests: bad scheme, alias taken, reserved alias, past expiry, expired link gives 410.
8. Try in `/docs`; commit.

Done when: `javascript:` URL gives 422, duplicate alias 409, alias `login` 422, expired link 410.

## Phase 3: Accounts and ownership

1. Install bcrypt and PyJWT; add SECRET_KEY to `.env`.
2. Add `users` model; add `user_id` (foreign key) and index (user_id, created_at DESC) to `urls`; new migration.
3. Helpers: hash password, check password, create token (60 min), read token.
4. Schemas: register, login, user, token response.
5. Register: lowercase email, hash password, insert, 409 if email exists.
6. Login: same 401 message for unknown email and wrong password.
7. Routes: register, login, `GET /api/auth/me`.
8. Dependencies: required current user; optional current user (anonymous allowed, bad token gives 401).
9. Shorten attaches owner when logged in.
10. `GET /api/links` (paged, newest first, status active/expired/disabled).
11. `DELETE /api/links/{code}`: owner only, soft delete (is_active false), 404 for others, 204.
12. Tests for auth and ownership; try with Swagger Authorize button; commit.

Done when: login works, my links lists only mine, another user deleting my link gets 404, bad token gets 401.

## Phase 4: Redis cache

1. Install Redis client; add REDIS_URL.
2. Redis connection helper.
3. Cache helper: get, set, delete key `url:{code}` (JSON: urlId, longUrl, expiresAt). TTL = shorter of 24 hours or time until expiry.
4. Redirect becomes cache-aside: Redis first, database on miss, store result.
5. Negative cache: unknown or disabled codes cached 60 seconds.
6. Write cache on create; delete cache on disable.
7. Counters for cache hits and misses.
8. Routes: `GET /api/metrics` (hits, misses, ratio), real `GET /api/health` (database and Redis checks).
9. Tests; request one link 100 times and check hit ratio near 0.99; disable link and check immediate 410.
10. Commit.

## Phase 5: Rate limiter and API keys

1. Work through the token bucket by hand (10 per minute example).
2. Write the Lua script: refill, take one token, return allowed or seconds to wait; use Redis clock.
3. Rate limiter helper loads and runs the script per request.
4. Policies in `.env`: redirect 120 bucket / 2 per sec; anonymous shorten 10/min; API key shorten 60/min; login and register 5/min; other API routes 60/min.
5. Reusable dependency on public routes: adds limit headers, returns 429 with Retry-After, fails open if Redis is down.
6. Client IP detection (trust forwarded header only behind Nginx).
7. Add `api_keys` model and migration (user_id, label, key_prefix, key_hash, created_at).
8. Routes: create key (random, prefix `sk_live_`, store SHA-256 only, show once, max 5), list, revoke.
9. Accept `X-API-Key` in authentication.
10. Tests: 11 anonymous shortens give ten 201s then 429; wait and retry works; valid key works, revoked key gives 401.
11. Commit.

## Phase 6: Click analytics

1. Install user-agent parser (country lookup optional; skip at first, store empty).
2. Add `click_events` model and migration; index (url_id, clicked_at).
3. On redirect, push a click event to a Redis Stream; ignore failures so redirect never breaks.
4. Create the consumer group.
5. Worker (separate process): read up to 100 events, parse device and referrer host, drop the IP, insert in one batch, add to click_count, acknowledge.
6. Expiry job: periodically mark expired links inactive.
7. Stats logic: four grouped queries (per day or hour, referrers, devices, countries); fill empty days with 0; range 1d, 7d, 30d.
8. Route `GET /api/links/{code}/stats` (owner only).
9. Test: 5 clicks appear; stop worker and lag grows; restart drains it.
10. Commit.

## Phase 7: React frontend

1. Create the Vite React app in `frontend`; proxy `/api` to port 8000.
2. Install React Router and a chart library.
3. One API helper file: attaches token, handles errors the same way everywhere.
4. Auth state: store token, call `/me` on start; navigation bar.
5. Pages: Shorten, My links, Analytics, Login/Register, API keys.
6. Loading, error and 429 messages ("try again in N seconds") on every page.
7. Run the full scenario in the browser; production build succeeds.
8. Commit.

## Phase 8: Scale, measure, ship

1. Dockerfile for the API (the worker reuses it).
2. Compose file: database, Redis, two API instances, worker, Nginx, frontend.
3. Nginx: round-robin between instances, pass client IP, serve frontend.
4. Add `X-Served-By` response header.
5. Verify the header alternates; stop one instance and confirm the site still works.
6. k6 load test on redirects, cache off then on. Record: requests per second, p95 latency, cache hit ratio, requests allowed vs rejected by the limiter.
7. GitHub Actions: lint and tests on every push.
8. Docs folder: why Base62, why 302 not 301, sequence vs hash vs Snowflake IDs, scaling to billions, fixed vs sliding window vs token bucket.
9. README: what it does, screenshot, architecture diagram, setup steps, tech stack, API list, measured numbers.
10. Deploy; add live link and GitHub link to resume.
11. Fill resume bullets with your real numbers; delete any bullet you cannot measure.

Done when: one command runs everything on a clean checkout, tests are green in CI, live link works, every number is measured.

---

## If you switch to TypeScript

Same phases and design. Replace: virtual environment with npm; FastAPI with Express or Fastify; SQLAlchemy and Alembic with Prisma and Prisma Migrate; Pydantic with Zod; PyJWT and bcrypt with jsonwebtoken and bcryptjs; redis-py with ioredis; pytest with Jest or Vitest. Database tables, routes, Redis keys and Lua script stay the same.
