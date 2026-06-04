import axios from "axios";
import { useAuthStore } from "../store/authStore";

export const client = axios.create({
  baseURL: "/",
  headers: { "Content-Type": "application/json" },
});

client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Shared in-flight refresh so concurrent 401s trigger only one /auth/refresh.
let refreshPromise: Promise<string> | null = null;

function refreshAccessToken(): Promise<string> {
  if (!refreshPromise) {
    const refresh = localStorage.getItem("refresh_token");
    if (!refresh) return Promise.reject(new Error("no_refresh_token"));
    refreshPromise = axios
      .post("/auth/refresh", { refresh_token: refresh })
      .then(({ data }) => {
        useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
        return data.access_token as string;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

client.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    // 401 = expired/invalid token, 403 = missing token (HTTPBearer with auto_error=True)
    if ((err.response?.status === 401 || err.response?.status === 403) && original && !original._retry) {
      original._retry = true;
      try {
        const accessToken = await refreshAccessToken();
        original.headers.Authorization = `Bearer ${accessToken}`;
        return client(original);
      } catch {
        useAuthStore.getState().clearAuth();
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

export default client;
