import { create } from "zustand";
import type { UserResponse } from "../api/auth";

interface AuthState {
  user: UserResponse | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  setTokens: (access: string, refresh: string) => void;
  setUser: (user: UserResponse) => void;
  clearAuth: () => void;
}

const stored = {
  refresh: localStorage.getItem("refresh_token"),
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null, // Never persisted to localStorage; held in memory only (XSS mitigation)
  refreshToken: stored.refresh,
  isAuthenticated: !!stored.refresh,

  setTokens: (access, refresh) => {
    localStorage.setItem("refresh_token", refresh);
    // access_token intentionally NOT written to localStorage
    set({ accessToken: access, refreshToken: refresh, isAuthenticated: true });
  },

  setUser: (user) => set({ user }),

  clearAuth: () => {
    localStorage.removeItem("refresh_token");
    set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false });
  },
}));
