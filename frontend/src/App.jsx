import { useCallback, useState } from "react";
import { loadSavedToken, saveToken } from "./api.js";
import Dashboard from "./components/Dashboard.jsx";
import Login from "./components/Login.jsx";

// Top level: show the login form when there is no token, otherwise the dashboard.
export default function App() {
  const [token, setToken] = useState(() => loadSavedToken());
  const [sessionMessage, setSessionMessage] = useState("");

  function handleLoggedIn(newToken) {
    saveToken(newToken);
    setSessionMessage("");
    setToken(newToken);
  }

  // useCallback keeps this function identical between renders, so the
  // dashboard's polling timers are not restarted needlessly.
  const handleSignedOut = useCallback((message) => {
    saveToken(null);
    setSessionMessage(typeof message === "string" ? message : "");
    setToken(null);
  }, []);

  if (!token) {
    return <Login onLoggedIn={handleLoggedIn} sessionMessage={sessionMessage} />;
  }
  return <Dashboard token={token} onSignOut={() => handleSignedOut("")} onSignedOut={handleSignedOut} />;
}
