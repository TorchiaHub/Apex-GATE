import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, register } from "../api/auth";
import { useAuthStore } from "../store/authStore";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import styles from "./Login.module.css";

export default function Login() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { setTokens } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "register") {
        await register(username, email, password);
      }
      const tokens = await login(username, password);
      setTokens(tokens.access_token, tokens.refresh_token);
      navigate("/", { replace: true });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.brand}>
          <div className={styles.mark}>▲</div>
          <h1 className={styles.title}>APEX GATE</h1>
          <p className={styles.subtitle}>{mode === "login" ? "Sign in to your gateway" : "Create your account"}</p>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          <Input label="Username" type="text" value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus autoComplete="username" />
          {mode === "register" && (
            <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
          )}
          <Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete={mode === "login" ? "current-password" : "new-password"} />

          {error && <p className={styles.error}>{error}</p>}

          <Button type="submit" className={styles.submit} loading={loading}>
            {mode === "login" ? "Sign in" : "Create account"}
          </Button>
        </form>

        <p className={styles.toggle}>
          {mode === "login" ? "New here?" : "Already have an account?"}
          <button className={styles.toggleBtn} onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
            {mode === "login" ? "Create account" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}
