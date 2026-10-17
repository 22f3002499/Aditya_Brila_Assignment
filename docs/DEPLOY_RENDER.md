# Deploying on Render (free plan)

You will create **two** Render services from one GitHub repository:

1. `economic-dashboard-api` – FastAPI (Web Service)
2. `economic-dashboard-web` – React (Static Site)

The two services depend on each other's URL, so the order below matters.

## Step 0 – Put the code on GitHub
1. Create an empty repository on github.com (e.g. `economic-dashboard`).
2. In the project folder run:
   ```bash
   git init
   git add .
   git commit -m "Economic dashboard"
   git branch -M main
   git remote add origin https://github.com/<your-name>/economic-dashboard.git
   git push -u origin main
   ```
3. Check that no `.env` file was committed (the `.gitignore` already excludes them).

## Step 1 – Create the API (Web Service)
1. Sign up / log in at https://render.com (you can use your GitHub account) and connect your GitHub.
2. **New + → Web Service** → choose your repository.
3. Fill in:
   | Field | Value |
   |---|---|
   | Name | `economic-dashboard-api` |
   | Root Directory | `backend` |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Instance Type | **Free** |
4. Under **Advanced** set **Health Check Path** to `/health`.
5. Add **Environment Variables**:
   | Key | Value |
   |---|---|
   | `PYTHON_VERSION` | `3.12.7` |
   | `JWT_SECRET` | a long random string (generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`) |
   | `EVAL_USERNAME` | e.g. `panel` |
   | `EVAL_PASSWORD` | a strong password you will share privately with the panel |
   | `DATABASE_PATH` | `/tmp/dashboard.db` |
   | `FRONTEND_ORIGIN` | leave a temporary value such as `https://placeholder.onrender.com` – you will fix it in Step 3 |
6. Click **Create Web Service**. Wait until the deploy shows **Live**.
7. Copy the API URL (like `https://economic-dashboard-api.onrender.com`) and open `<API URL>/health` – you should see `{"status":"ok",...}`. `<API URL>/docs` shows the interactive API documentation.

## Step 2 – Create the frontend (Static Site)
1. **New + → Static Site** → same repository.
2. Fill in:
   | Field | Value |
   |---|---|
   | Name | `economic-dashboard-web` |
   | Root Directory | `frontend` |
   | Build Command | `npm install && npm run build` |
   | Publish Directory | `dist` |
3. Add the environment variable `VITE_API_BASE_URL` = your API URL from Step 1 (no trailing slash).
4. Open the **Redirects/Rewrites** tab and add a rewrite: Source `/*`, Destination `/index.html`, Action **Rewrite**.
5. **Create Static Site** and wait for **Live**. Copy the site URL (like `https://economic-dashboard-web.onrender.com`).

## Step 3 – Allow the frontend to call the API (CORS)
1. Go back to the **API** service → **Environment**.
2. Change `FRONTEND_ORIGIN` to the exact frontend URL from Step 2 (`https://economic-dashboard-web.onrender.com`, no trailing slash).
3. Save – Render redeploys the API automatically.

## Step 4 – Test
1. Open the frontend URL and sign in with `EVAL_USERNAME` / `EVAL_PASSWORD`.
2. Wait about 30–60 seconds on the first visit (the free API wakes up and the collector fetches data). Panels show "Loading…" and then fill in.
3. If the ticker shows OFFLINE/`---`, NSE may be refusing the cloud IP – see "Troubleshooting".

## Alternative: one-click Blueprint
Instead of Steps 1–2 you can choose **New + → Blueprint**, pick the repository, and Render reads `render.yaml` and creates both services. You will be asked for `FRONTEND_ORIGIN`, `EVAL_USERNAME`, `EVAL_PASSWORD` and `VITE_API_BASE_URL`; the API URL is only known after the first deploy, so fill in a placeholder, then update the values (Steps 2–3) and redeploy.

## Things to know about the free plan
* **Sleeping**: the API sleeps after ~15 min without requests; the first request afterwards is slow. Open the site a minute before your demo, or ping `/health` (e.g. with the free UptimeRobot service) to keep it awake.
* **Ephemeral disk**: the SQLite database is wiped on restarts/redeploys. This is fine – the collector refills it and the evaluation user is re-created from the env vars.
* The frontend and the API are separate hosted services with different URLs, both on HTTPS.

## Submission checklist
- Frontend URL, API URL (`/docs`) and health URL (`/health`).
- Evaluation username/password – send privately, never in the repository.
- Portfolio website URL + flagship projects (role, technologies, what you built).
- Assumptions / limitations: copy section 10 of the README.
- Screen-recording explaining flow, challenges, decisions and AI usage (see the assignment, section V).

## Troubleshooting
| Symptom | Fix |
|---|---|
| Login shows "Cannot reach the server" | `VITE_API_BASE_URL` wrong, or the API is still waking up. After changing it, **redeploy the static site** (the value is baked in at build time). |
| Browser console shows a CORS error | `FRONTEND_ORIGIN` must equal the frontend URL exactly (https, no trailing slash). |
| Refreshing a page gives 404 on the static site | Add the `/*` → `/index.html` rewrite (Step 2.4). |
| Macro panels say "Data unavailable" | Check the API logs for `[collector]` lines; the World Bank may have timed out – it retries every 15 minutes. |
| Ticker OFFLINE | NSE often blocks cloud IPs. The app shows `---` instead of inventing values. Mention this limitation in your README/video, or run the API somewhere with a residential/other IP. |
| Every 401 after a while | Tokens expire after 60 minutes; sign in again. |
