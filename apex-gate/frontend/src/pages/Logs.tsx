import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchLogs } from "../api/logs";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";

const STATUS_VARIANT: Record<string, "success" | "error" | "warning" | "neutral"> = {
  success: "success",
  rate_limited: "warning",
  budget_exceeded: "warning",
  error: "error",
  all_exhausted: "error",
};

export default function Logs() {
  const [offset, setOffset] = useState(0);
  const [status, setStatus] = useState("");
  const limit = 50;

  const { data: logs = [], isFetching } = useQuery({
    queryKey: ["logs", offset, status],
    queryFn: () => fetchLogs({ limit, offset, status: status || undefined }),
    refetchInterval: 15_000,
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "var(--space-3)" }}>
        <div>
          <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: "var(--weight-bold)", letterSpacing: "-0.02em" }}>Request Logs</h1>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginTop: "var(--space-1)" }}>All proxy requests — auto-refreshes every 15 s</p>
        </div>
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setOffset(0); }}
          style={{ background: "var(--color-bg-elevated)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "var(--space-2) var(--space-3)", color: "var(--color-text-secondary)", fontSize: "var(--text-sm)" }}
        >
          <option value="">All statuses</option>
          <option value="success">Success</option>
          <option value="rate_limited">Rate limited</option>
          <option value="budget_exceeded">Budget exceeded</option>
          <option value="error">Error</option>
          <option value="all_exhausted">All exhausted</option>
        </select>
      </div>

      <Card style={{ padding: 0, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--text-xs)" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
              {["Time", "Model", "Tokens in", "Tokens out", "Cost", "Latency", "Status"].map((h) => (
                <th key={h} style={{ padding: "var(--space-3) var(--space-4)", textAlign: "left", color: "var(--color-text-muted)", fontWeight: "var(--weight-semibold)", whiteSpace: "nowrap" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 && !isFetching && (
              <tr><td colSpan={7} style={{ padding: "var(--space-6)", textAlign: "center", color: "var(--color-text-muted)" }}>No logs found</td></tr>
            )}
            {logs.map((l) => (
              <tr key={l.id} style={{ borderBottom: "1px solid var(--color-border-subtle)" }}>
                <td style={{ padding: "var(--space-3) var(--space-4)", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)", whiteSpace: "nowrap" }}>
                  {new Date(l.created_at).toLocaleTimeString()}
                </td>
                <td style={{ padding: "var(--space-3) var(--space-4)", color: "var(--color-text-secondary)", fontFamily: "var(--font-mono)", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {l.model_id ?? "—"}
                </td>
                <td style={{ padding: "var(--space-3) var(--space-4)", fontVariantNumeric: "tabular-nums", color: "var(--color-text-secondary)" }}>{l.input_tokens ?? "—"}</td>
                <td style={{ padding: "var(--space-3) var(--space-4)", fontVariantNumeric: "tabular-nums", color: "var(--color-text-secondary)" }}>{l.output_tokens ?? "—"}</td>
                <td style={{ padding: "var(--space-3) var(--space-4)", fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)" }}>
                  {parseFloat(l.cost_usd) > 0 ? `$${parseFloat(l.cost_usd).toFixed(5)}` : "—"}
                </td>
                <td style={{ padding: "var(--space-3) var(--space-4)", fontVariantNumeric: "tabular-nums", color: "var(--color-text-secondary)" }}>
                  {l.latency_ms != null ? `${l.latency_ms}ms` : "—"}
                </td>
                <td style={{ padding: "var(--space-3) var(--space-4)" }}>
                  <Badge variant={STATUS_VARIANT[l.status] ?? "neutral"}>{l.status.replace(/_/g, " ")}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "center" }}>
        <Button variant="secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>← Prev</Button>
        <Button variant="secondary" disabled={logs.length < limit} onClick={() => setOffset(offset + limit)}>Next →</Button>
      </div>
    </div>
  );
}
