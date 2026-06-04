import { NavLink, useNavigate } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";
import { logout } from "../../api/auth";
import styles from "./Sidebar.module.css";

const NAV = [
  {
    section: "Overview",
    items: [
      { to: "/", label: "Dashboard", icon: "◈" },
      { to: "/chat", label: "Chat", icon: "◐" },
      { to: "/stats", label: "Stats", icon: "◉" },
    ],
  },
  {
    section: "Keys",
    items: [
      { to: "/keys", label: "API Keys", icon: "⚿" },
      { to: "/virtual-keys", label: "Virtual Keys", icon: "⬡" },
    ],
  },
  {
    section: "Observability",
    items: [
      { to: "/logs", label: "Request Logs", icon: "≡" },
      { to: "/providers", label: "Providers", icon: "⬗" },
      { to: "/models", label: "Models", icon: "⬙" },
    ],
  },
];

const ADMIN_ITEMS = [{ to: "/admin", label: "Admin", icon: "⚙" }];
const SETTINGS_ITEM = { to: "/settings", label: "Settings", icon: "⚒" };

export function Sidebar() {
  const { user, refreshToken, clearAuth } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      if (refreshToken) await logout(refreshToken);
    } catch { /* ignore */ }
    clearAuth();
    navigate("/login");
  };

  return (
    <aside className={styles.sidebar} aria-label="Main navigation">
      <div className={styles.logo}>
        <div className={styles.logoMark}>▲</div>
        <div>
          <div className={styles.logoText}>APEX GATE</div>
          <div className={styles.logoSub}>LLM Proxy</div>
        </div>
      </div>

      <nav className={styles.nav}>
        {NAV.map((group) => (
          <div key={group.section}>
            <div className={styles.section}>{group.section}</div>
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}
              >
                <span className={styles.icon} aria-hidden="true">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </div>
        ))}

        {user?.is_admin && (
          <div>
            <div className={styles.section}>System</div>
            {ADMIN_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}
              >
                <span className={styles.icon} aria-hidden="true">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </div>
        )}

        <div>
          <div className={styles.section}>Preferences</div>
          <NavLink
            to={SETTINGS_ITEM.to}
            className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}
          >
            <span className={styles.icon} aria-hidden="true">{SETTINGS_ITEM.icon}</span>
            {SETTINGS_ITEM.label}
          </NavLink>
        </div>
      </nav>

      <div className={styles.footer}>
        <div className={styles.userChip} onClick={handleLogout} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") handleLogout(); }} role="button" tabIndex={0} aria-label="Sign out">
          <div className={styles.avatar}>{user?.username?.[0]?.toUpperCase() ?? "?"}</div>
          <span className={styles.username}>{user?.username ?? "—"}</span>
          <span style={{ color: "var(--color-text-muted)", fontSize: "var(--text-xs)" }}>Exit</span>
        </div>
      </div>
    </aside>
  );
}
