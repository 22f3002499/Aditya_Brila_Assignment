// All communication with the FastAPI backend lives in this file.

// The backend address comes from the environment (set at build time), never hard-coded.
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

// Where the login token is kept. sessionStorage is cleared when the tab closes.
const TOKEN_STORAGE_KEY = "economic_dashboard_token";

export function loadSavedToken() {
  try {
    return sessionStorage.getItem(TOKEN_STORAGE_KEY);
  } catch (error) {
    return null; // storage can be blocked in private windows
  }
}

export function saveToken(token) {
  try {
    if (token) sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    else sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch (error) {
    // Ignore: the user simply has to sign in again after a reload.
  }
}

// An error that remembers the HTTP status, so callers can react to 401 (signed out).
export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function sendRequest(path, options) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, options);
  } catch (networkError) {
    throw new ApiError("Cannot reach the server", 0);
  }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const errorBody = await response.json();
      if (typeof errorBody.detail === "string") message = errorBody.detail;
    } catch (parseError) {
      // keep the generic message
    }
    throw new ApiError(message, response.status);
  }
  return response.json();
}

export function login(username, password) {
  return sendRequest("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export function fetchDashboard(token) {
  return sendRequest("/api/dashboard", { headers: { Authorization: `Bearer ${token}` } });
}

export function fetchTicker(token) {
  return sendRequest("/api/ticker", { headers: { Authorization: `Bearer ${token}` } });
}
