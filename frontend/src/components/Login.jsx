import { useState } from "react";
import { login } from "../api.js";

// Sign-in form. On success it hands the JWT to the parent through onLoggedIn.
export default function Login({ onLoggedIn, sessionMessage }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault(); // do not reload the page
    setErrorMessage("");
    setIsSubmitting(true);
    try {
      const result = await login(username.trim(), password);
      onLoggedIn(result.access_token);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>ECONOMIC INDICATOR</h1>
        <p className="login-hint">Sign in to view the dashboard</p>

        {sessionMessage && <div className="login-notice">{sessionMessage}</div>}

        <label htmlFor="username">Username</label>
        <input id="username" value={username} onChange={(e) => setUsername(e.target.value)}
               autoComplete="username" required maxLength={64} />

        <label htmlFor="password">Password</label>
        <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
               autoComplete="current-password" required maxLength={200} />

        {errorMessage && <div className="login-error" role="alert">{errorMessage}</div>}

        <button type="submit" disabled={isSubmitting}>{isSubmitting ? "Signing in…" : "Sign in"}</button>
      </form>
    </main>
  );
}
