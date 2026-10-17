"""FastAPI application: routes, authentication guard, CORS and background tasks."""

import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from . import collector, database, security, service
from .config import settings
from .indicators import INDICATORS


# ---------------------------------------------------------------- startup / shutdown

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Make sure the database tables exist.
    database.create_tables()

    # 2. Create (or update) the evaluation account for the interview panel.
    if settings.eval_username and settings.eval_password:
        database.create_or_update_user(
            settings.eval_username, security.hash_password(settings.eval_password)
        )

    # 3. Start the background collector loops.
    background_tasks = []
    if settings.enable_collector:
        background_tasks.append(asyncio.create_task(collector.run_ticker_loop()))
        background_tasks.append(asyncio.create_task(collector.run_macro_loop()))

    yield  # the API serves requests while we are paused here

    for task in background_tasks:
        task.cancel()


app = FastAPI(title="Economic Indicators API", version="1.0.0", lifespan=lifespan)

# CORS: only the deployed frontend origin may call this API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# ---------------------------------------------------------------- login protection

# Very small in-memory brake against password guessing:
# at most 5 failed attempts per (username, client address) in 5 minutes.
MAX_FAILED_LOGINS = 5
FAILED_LOGIN_WINDOW_SECONDS = 300
failed_login_times = {}


def count_recent_failures(attempt_key: str) -> int:
    cutoff_time = time.time() - FAILED_LOGIN_WINDOW_SECONDS
    recent_times = [t for t in failed_login_times.get(attempt_key, []) if t > cutoff_time]
    failed_login_times[attempt_key] = recent_times
    return len(recent_times)


# ---------------------------------------------------------------- request / response models

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=200)


bearer_scheme = HTTPBearer(auto_error=False)


def require_signed_in_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    """Dependency used by protected routes. Returns the username or raises 401."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    username = security.read_username_from_token(credentials.credentials)
    if username is None or database.find_user_by_username(username) is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    return username


# ---------------------------------------------------------------- public routes

@app.get("/health", tags=["system"])
def health_check():
    """Public health check used by Render and by the interview panel."""
    database_ok = database.check_database_is_working()
    return {
        "status": "ok" if database_ok else "degraded",
        "database": "ok" if database_ok else "unreachable",
        "collector_enabled": settings.enable_collector,
        "time": database.current_utc_text(),
    }


@app.post("/api/auth/login", tags=["auth"])
def login(login_request: LoginRequest, request: Request):
    client_address = request.client.host if request.client else "unknown"
    attempt_key = f"{login_request.username.lower()}|{client_address}"

    if count_recent_failures(attempt_key) >= MAX_FAILED_LOGINS:
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in a few minutes.")

    user = database.find_user_by_username(login_request.username)
    # Always run the hash check (against a dummy hash for unknown users) so timing is equal.
    stored_hash = user["password_hash"] if user else security.DUMMY_HASH
    password_is_correct = security.password_matches(login_request.password, stored_hash)

    if user is None or not password_is_correct:
        failed_login_times.setdefault(attempt_key, []).append(time.time())
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    failed_login_times.pop(attempt_key, None)
    return {
        "access_token": security.create_access_token(user["username"]),
        "token_type": "bearer",
        "expires_in": settings.jwt_expire_minutes * 60,
    }


# ---------------------------------------------------------------- protected routes

@app.get("/api/auth/me", tags=["auth"])
def who_am_i(username: str = Depends(require_signed_in_user)):
    return {"username": username}


@app.get("/api/dashboard", tags=["dashboard"])
def get_dashboard(username: str = Depends(require_signed_in_user)):
    """All seven indicators (ticker + six panels) in one response."""
    return service.build_dashboard_response()


@app.get("/api/ticker", tags=["dashboard"])
def get_ticker(username: str = Depends(require_signed_in_user)):
    """Only the market ticker. Small and cheap, so the browser polls it often."""
    return service.build_indicator_response("ticker")


@app.get("/api/indicators/{indicator_key}", tags=["dashboard"])
def get_indicator(indicator_key: str, username: str = Depends(require_signed_in_user)):
    if indicator_key not in INDICATORS:
        raise HTTPException(status_code=404, detail="Unknown indicator")
    return service.build_indicator_response(indicator_key)
