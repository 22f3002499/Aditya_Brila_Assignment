# Economic Indicators Dashboard

React (Vite) frontend + FastAPI backend + SQLite, built for the *Interview Round II* assignment.
A server-side collector gathers data from **NSE India** (live ticker) and the **World Bank** (macro indicators),
validates it, stores it in a database, and the browser reads it only through the authenticated API.

```
Browser (React) --HTTPS+JWT--> FastAPI --reads--> SQLite  <--writes-- Collector (background tasks)
                                                                         |-- NSE India  (ticker)
                                                                         '-- World Bank / curated CSV (macro)
```

## 1. Features

| Requirement | How it is done |
|---|---|
| Ticker + 6 panels | GDP, Debt/GDP, Trade, GST, Inflation, Government Expenditure (`frontend/src/components/`) |
| Browser never scrapes NSE | Only `backend/app/sources/nse.py` calls NSE; the browser calls `/api/...` |
| Validation, timeouts, caching | `validators.py`, per-request timeout, results cached in SQLite and served from there |
| Stale / loading / error / empty states | Panel banner, spinner, "Data unavailable", "No data points"; missing numbers show `---` |
| Never invent data | Missing → `null` → `---`; a failed refresh keeps the last valid snapshot and marks it **stale** |
| Rate-aware collector | Ticker every 60 s while market open, every 30 min when closed, exponential back-off on failure (max 10 min); macro every 12 h |
| Frontend updates | Documented equivalent of SSE: **polling** the API (ticker every 30 s, panels every 5 min). Polling is cheap because the API only reads its own database |
| JWT auth | `POST /api/auth/login`, HS256, 60-minute expiry, all data routes protected |
| DB not public | SQLite file on the API server; no network port exists at all |
| CORS | Only `FRONTEND_ORIGIN` is allowed |
| Health check | `GET /health` |

## 2. Data sources, dates and limitations

Every panel shows its **source** and **"as of"** period; non-NSE sources are labelled "(non-NSE)".

| Indicator | Source | Transformation / limitation |
|---|---|---|
| Ticker | NSE `allIndices` (public). "As of" = NSE's own timestamp | **SENSEX is a BSE index, not published by NSE**, so the ticker shows NIFTY 50, BANK, IT, NEXT 50, etc. NSE can block cloud IPs; if so the ticker shows OFFLINE/`---` rather than fake values |
| GDP growth (India, World) | World Bank `NY.GDP.MKTP.KD.ZG` | Annual %, latest year published (usually ~1 year behind). Change = difference vs previous year (pp) |
| Debt to GDP (India, USA) | World Bank `GC.DOD.TOTL.GD.ZS` (central government debt) | Annual; coverage for some years/countries may be missing (shown as gaps / `---`). The design's daily-looking line is shown as an annual line because no free daily source exists. Second card shows the **United States** value (the design's "Ind vs US") |
| Exports / Imports / Balance | World Bank `NE.EXP.GNFS.CD`, `NE.IMP.GNFS.CD` | US$ → billions. Balance = exports − imports, only where both exist |
| GST collection | **Curated CSV** `backend/app/data/gst_collections.csv` (Ministry of Finance / PIB press releases) | No free API exists. Annual gross collection (₹ lakh crore); monthly average = total ÷ 12. **Verify figures against PIB before submitting; update the CSV when new data is published** |
| Inflation | World Bank `FP.CPI.TOTL.ZG` (CPI, annual %) | RBI target 4 % (±2 %) is a policy constant in `indicators.py` |
| Government expenditure | **Curated CSV** `backend/app/data/union_budget_expenditure.csv` (Union Budget documents) | ₹ lakh crore. Revenue = total − capital. Latest year may be a Revised Estimate (see `basis` column). **Verify against the Budget documents before submitting** |

## 3. Design choices where the brief left behaviour open

* **Controls**: clicking a legend entry shows/hides that series; the **5Y / 10Y** switch changes how many years every chart shows; **Sign out** clears the token; hovering a chart shows a tooltip; hovering the ticker pauses it.
* Change pills are green ▲ when ≥ 0 and red ▼ when negative (the Figma reference shows green for all). Units: `pp` = percentage points, `%` = percent growth.
* Icons/flags are simple inline SVG drawings, not the 3D images in the Figma file.
* Charts use calendar/fiscal **years** on the x-axis because the sources are annual.

## 4. Project layout

```
backend/
  app/main.py          routes, CORS, auth guard, startup
  app/config.py        environment settings
  app/database.py      SQL (parameterized) + schema bootstrap
  app/security.py      scrypt password hashing, JWT
  app/collector.py     background refresh loops
  app/indicators.py    how each panel's data is built
  app/sources/         nse.py, worldbank.py, curated.py
  app/validators.py    number / series validation helpers
  app/service.py       builds API responses + status (ok/stale/unavailable/pending)
  app/create_user.py   CLI to add a user
  schema.sql           database schema
  tests/test_api.py    17 tests (auth, CORS, stale handling, parsers)
frontend/src/          App, api.js, components/ (Dashboard, Panel, Ticker, Charts, Login ...)
render.yaml            Render blueprint (both services)
docs/DEPLOY_RENDER.md      step-by-step free deployment
docs/CODE_WALKTHROUGH.md   plain-language explanation of the code
```

## 5. Run locally

Requirements: Python 3.11+, Node 18+.

```bash
# --- backend (terminal 1) ---
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env     # edit the values, then load them into your shell:
export $(grep -v '^#' .env | xargs)                    # PowerShell: set each one with $env:NAME="value"
uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs     health: http://localhost:8000/health

# --- frontend (terminal 2) ---
cd frontend
cp .env.example .env     # VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev              # http://localhost:5173
```

Sign in with `EVAL_USERNAME` / `EVAL_PASSWORD`. Data appears within seconds of start-up (the collector runs immediately). Run the tests with `cd backend && pytest`.

## 6. API reference

Base URL = your API URL. Protected routes need the header `Authorization: Bearer <token>`; otherwise **401**.

| Method & path | Auth | Request | Response |
|---|---|---|---|
| `GET /health` | no | – | `{"status":"ok","database":"ok","collector_enabled":true,"time":"..."}` |
| `POST /api/auth/login` | no | `{"username":"...","password":"..."}` | `{"access_token":"<jwt>","token_type":"bearer","expires_in":3600}`; **401** wrong credentials; **429** after 5 failures / 5 min |
| `GET /api/auth/me` | yes | – | `{"username":"panel"}` |
| `GET /api/dashboard` | yes | – | `{"generated_at":"...","indicators":{ticker,gdp,debt,trade,gst,inflation,expenditure}}` |
| `GET /api/ticker` | yes | – | one indicator object (below) |
| `GET /api/indicators/{key}` | yes | key ∈ `ticker,gdp,debt,trade,gst,inflation,expenditure` | one indicator object; **404** unknown key |

Indicator object:
```json
{ "key": "gdp", "title": "...", "status": "ok | stale | unavailable | pending",
  "source": {"name": "...", "url": "...", "is_nse": false},
  "as_of": "2024", "fetched_at": "2026-10-17T02:49:59+00:00", "last_error": null,
  "data": { "years": [2020, 2021], "series": {"india": [8.1, null]},
            "summary": {"india": {"value": 8.1, "change": 0.4, "period": "2020"}} } }
```
`null` = missing value (UI shows `---`). `status`: **pending** = collector has not finished its first try; **unavailable** = tried, no data at all; **stale** = last refresh failed (or data very old) but older valid data is shown; **ok** = fresh.

## 7. Environment variables

| Backend | Meaning | Default |
|---|---|---|
| `JWT_SECRET` | signing key, ≥ 32 chars (**required in production**) | random per start |
| `JWT_EXPIRE_MINUTES` | token lifetime | 60 |
| `FRONTEND_ORIGIN` | allowed CORS origin(s), comma-separated | `http://localhost:5173` |
| `EVAL_USERNAME`, `EVAL_PASSWORD` | evaluation account created/updated at start-up | none |
| `DATABASE_PATH` | SQLite file | `backend/data/dashboard.db` |
| `ENABLE_COLLECTOR` | `false` disables background refresh | true |
| `TICKER_REFRESH_SECONDS` | market-hours ticker interval (min 30) | 60 |
| `MACRO_REFRESH_HOURS` | macro interval | 12 |
| `UPSTREAM_TIMEOUT_SECONDS` | per-request timeout | 10 |

| Frontend (build time) | Meaning |
|---|---|
| `VITE_API_BASE_URL` | URL of the API |

## 8. Authentication and token handling

* Passwords are stored only as salted **scrypt** hashes (`users` table). There is no public sign-up.
* Login returns a **JWT (HS256)** with `sub`, `iat`, `exp` (default 60 min). Expired/invalid tokens give 401 and the frontend returns to the login page with a message.
* The frontend keeps the token in `sessionStorage` (cleared when the tab closes) and sends it as a Bearer header. Trade-off: an XSS bug could read it; the app renders no user-generated HTML, and because no cookies are used there is no CSRF risk.
* **Granting panel access**: set `EVAL_USERNAME` / `EVAL_PASSWORD` in the Render dashboard (never in Git) and share the credentials with the panel privately. Rotate by changing the env value and redeploying. More users: `python -m app.create_user <name>`.
* Login throttling: 5 failed attempts per username+IP per 5 minutes (in memory).

## 9. Database

* SQLite (`backend/schema.sql`: `users`, `snapshots`, `fetch_status`), created automatically at start-up. All SQL is parameterized.
* **Not publicly reachable**: SQLite is a file opened only by the API process; it opens no TCP port, so there is nothing to bind or firewall. (If you later move to Postgres, use the host's private network and bind to the private address only.)
* On Render's free tier the disk is ephemeral: the DB is rebuilt by the collector after each restart/deploy (the evaluation user is re-created from the env vars).

## 10. Assumptions and known limitations

* NSE may refuse requests from data-centre IPs or change its endpoint; the app degrades to OFFLINE/stale and never fabricates numbers. A fallback or paid feed would be the production fix.
* GST and expenditure come from hand-maintained CSVs (no free API) – verify the numbers.
* Market holidays are not tracked (the ticker refreshes every 60 s on weekdays 09:15–15:30 IST).
* Render free web services sleep after ~15 minutes without traffic; the first request afterwards takes ~30–60 s and the collector restarts.
* Frontend (Render static site) and API (Render web service) are separate sites on separate hosts, both HTTPS. For even stronger separation host the frontend on Netlify/Vercel and only change `FRONTEND_ORIGIN`.
* The layout was built from the supplied reference image; check measurements against the Figma frame.

## 11. Deploy to Render for free

See [`docs/DEPLOY_RENDER.md`](docs/DEPLOY_RENDER.md).
