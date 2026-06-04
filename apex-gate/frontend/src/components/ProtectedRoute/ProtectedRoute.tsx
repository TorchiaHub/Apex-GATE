import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import axios from "axios";
import { useAuthStore } from "../../store/authStore";
import { getMe } from "../../api/auth";

export function ProtectedRoute() {
  const { isAuthenticated, accessToken, refreshToken, user, setUser, setTokens, clearAuth } = useAuthStore();
  const [initializing, setInitializing] = useState(!accessToken && !!refreshToken);

  useEffect(() => {
    // If we have a refresh token but no access token (e.g. after page reload),
    // proactively exchange it for a new access token before rendering children.
    if (!accessToken && refreshToken) {
      axios
        .post("/auth/refresh", { refresh_token: refreshToken })
        .then(({ data }) => {
          setTokens(data.access_token, data.refresh_token);
        })
        .catch(() => {
          clearAuth();
        })
        .finally(() => setInitializing(false));
    } else {
      setInitializing(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (accessToken && !user) {
      getMe().then(setUser).catch(() => {
        // If /auth/me fails the response interceptor in client.ts will
        // handle token refresh or redirect to /login automatically.
      });
    }
  }, [accessToken, user, setUser]);

  if (initializing) {
    return null; // or a spinner; wait for token init before deciding
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
