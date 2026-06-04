import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppShell } from "./components/Layout/AppShell";
import { ProtectedRoute } from "./components/ProtectedRoute/ProtectedRoute";

const Login = lazy(() => import("./pages/Login"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Chat = lazy(() => import("./pages/Chat"));
const ApiKeys = lazy(() => import("./pages/ApiKeys"));
const VirtualKeys = lazy(() => import("./pages/VirtualKeys"));
const Logs = lazy(() => import("./pages/Logs"));
const Providers = lazy(() => import("./pages/Providers"));
const Admin = lazy(() => import("./pages/Admin"));
const Stats = lazy(() => import("./pages/Stats"));
const Models = lazy(() => import("./pages/Models"));
const Settings = lazy(() => import("./pages/Settings"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      retry: 1,
    },
  },
});

const Loader = () => (
  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100dvh", color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
    Loading…
  </div>
);

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<Loader />}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppShell />}>
                <Route path="/" element={<Dashboard />} />
                <Route path="/chat" element={<Chat />} />
                <Route path="/keys" element={<ApiKeys />} />
                <Route path="/virtual-keys" element={<VirtualKeys />} />
                <Route path="/logs" element={<Logs />} />
                <Route path="/providers" element={<Providers />} />
                <Route path="/admin" element={<Admin />} />
                <Route path="/stats" element={<Stats />} />
                <Route path="/models" element={<Models />} />
                <Route path="/settings" element={<Settings />} />
              </Route>
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
