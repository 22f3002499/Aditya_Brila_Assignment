# Code walkthrough (in simple terms)

Read this before the interview. For every file: **what it does** and **why**.

## Big picture
1. A **collector** (background task in the API server) downloads data from NSE and the World Bank every so often.
2. It **checks** the data. Only valid data is saved in the **database**.
3. The browser logs in, receives a **token**, and asks the API for the saved data.
4. React draws the cards and charts. If data is old or missing, it says so instead of guessing.

## Backend (`backend/app`)

### `config.py`
Reads settings from environment variables (secret key, allowed website, refresh times). Keeping secrets here, outside the code, means they never end up on GitHub.

### `database.py`
All SQL lives here. Every query uses `?` placeholders, so typed text can never become SQL commands (this stops SQL injection).
* `save_snapshot` – saves good data and marks "last refresh worked".
* `record_failed_refresh` – only writes the error; the old good data stays. This is how "stale" works.

### `security.py`
* `hash_password` / `password_matches` – passwords are scrambled with a random salt (scrypt) so even we cannot read them.
* `create_access_token` / `read_username_from_token` – a JWT is a signed note saying "this is user X until time T". If anyone edits it, the signature no longer matches.

### `validators.py`
`to_number` turns anything into a real number or `None` (never a guess). `align_series_by_year` lines up several yearly series so charts can read them; gaps become `None`. `latest_value_with_change` finds the newest value and the change from the previous one.

### `sources/nse.py`
NSE only answers browsers that hold cookies, so we first open the home page, then ask for the data. `parse_nse_indices` throws an error if the reply looks wrong and skips bad rows.

### `sources/worldbank.py`
Asks the World Bank for one indicator of one country and converts the reply to `{year: value}`, skipping years without data.

### `sources/curated.py`
Reads the two CSV files (GST and expenditure) and checks them (for example capital spending cannot exceed total spending).

### `indicators.py`
One small function per panel that gets the data and builds `{years, series, summary}`. The `INDICATORS` table lists title, source and "how old is too old" for each panel.

### `collector.py`
Two endless loops. The ticker loop runs about every minute while the market is open, every 30 minutes otherwise, and waits longer after failures (back-off) so we never hammer NSE. The macro loop runs every 12 hours. `refresh_indicator` wraps everything in try/except: success → save; failure → record the error and keep the old data.

### `service.py`
Turns database rows into the API answer and decides the status: `ok`, `stale`, `unavailable` or `pending`.

### `main.py`
* Start-up: create tables, create the evaluation user, start the collector.
* CORS: only your frontend website may call the API.
* `/api/auth/login`: checks the password (always doing the hash work so timing does not reveal valid usernames), limits to 5 wrong tries per 5 minutes, returns a token.
* `require_signed_in_user`: protects routes; no valid token → 401.

### `create_user.py`
Command to add a user with a hidden password prompt.

## Frontend (`frontend/src`)

### `api.js`
The only file that talks to the backend. Reads the API address from `VITE_API_BASE_URL`, adds the token header, and turns failures into an `ApiError` carrying the status code.

### `App.jsx`
If there is no token show `Login`, else `Dashboard`. If the API says 401 (expired), it signs out and shows a message.

### `components/Dashboard.jsx`
`useDashboardData` fetches everything once, then re-fetches the ticker every 30 s and all panels every 5 min. If a refresh fails it keeps the old data and sets `connectionLost`, which makes panels show a "stale" warning. The page then lists the six panels, each described by two things: which stat cards to show and which chart to draw.

### `components/Panel.jsx`
The shared frame: title, warning banner, stat cards, chart area and the "Source … As of …" line. It picks what to show for loading / unavailable / empty / stale / ok.

### `components/StatCard.jsx`
Icon, label, big value and the green ▲ / red ▼ change. Missing numbers display `---`.

### `components/Ticker.jsx`
The scrolling bar with a LIVE / STALE / OFFLINE badge. The list is doubled so the scroll loops smoothly.

### `components/Charts.jsx`
Six chart components built with Recharts. `buildRows` converts the API shape to one row per year and applies the 5Y/10Y choice. `useHiddenSeries` remembers legend clicks. `GradientDefinitions` holds the blue/orange gradients once for all charts.

### `format.js`
`formatNumber` and friends; everything missing becomes `---` in one place.

### `styles.css`
The dark theme. The page is a two-column, three-row grid that exactly fills 1214 × 2159 without horizontal scrolling, and becomes one column on narrow screens.

## Questions to be ready for
* *Why polling and not SSE?* Simpler, works through proxies, and the API only reads its own database so it is cheap. SSE would need a token in the URL because `EventSource` cannot send headers.
* *Why SQLite?* One server, tiny data, and no network port means it cannot be reached publicly.
* *Why World Bank?* NSE does not publish GDP, inflation, trade or debt.
* *Weak points?* NSE may block cloud IPs; curated CSV figures need manual updates; free tier sleeps and loses its disk.
