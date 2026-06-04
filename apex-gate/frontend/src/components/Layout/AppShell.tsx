import { useEffect } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import { getMe } from "../../api/auth";
import { Sidebar } from "./Sidebar";
import styles from "./AppShell.module.css";

export function AppShell() {
  const { isAuthenticated, setUser, clearAuth } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/login", { replace: true });
      return;
    }
    getMe().then(setUser).catch(() => {
      clearAuth();
      navigate("/login", { replace: true });
    });
  }, [isAuthenticated, navigate, setUser, clearAuth]);

  if (!isAuthenticated) return null;

  return (
    <div className={styles.shell}>
      <Sidebar />
      <div className={styles.main}>
        <main className={styles.content}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
