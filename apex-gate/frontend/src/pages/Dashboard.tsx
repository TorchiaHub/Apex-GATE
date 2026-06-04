import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchByDay, fetchByProvider, fetchOverview } from "../api/stats";
import { useProviderStatus } from "../hooks/useProviderStatus";
import { Card } from "../components/ui/Card";
import styles from "./Dashboard.module.css";

export default function Dashboard() {
  const { data: overview } = useQuery({ queryKey: ["overview"], queryFn: fetchOverview, refetchInterval: 30_000 });
  const { data: byDay } = useQuery({ queryKey: ["byDay"], queryFn: fetchByDay, refetchInterval: 60_000 });
  const { data: byProvider } = useQuery({ queryKey: ["byProvider"], queryFn: fetchByProvider, refetchInterval: 30_000 });
  const wsStatus = useProviderStatus();

  const maxCalls = Math.max(...(byProvider?.map((p) => p.calls) ?? [1]), 1);

  return (
    <div className={styles.page}>
      <div className={styles.heading}>
        <h1 className={styles.title}>Dashboard</h1>
        <p className={styles.subtitle}>Live overview of your LLM proxy gateway</p>
      </div>

      <div className={styles.kpis}>
        {[
          { label: "Calls today", value: overview?.calls_today?.toLocaleString() ?? "—", sub: "requests" },
          { label: "Tokens today", value: overview?.tokens_today ? (overview.tokens_today / 1000).toFixed(1) + "k" : "—", sub: "prompt + completion" },
          { label: "Cost today", value: overview?.cost_today ? "$" + parseFloat(overview.cost_today).toFixed(4) : "—", sub: "estimated USD" },
        ].map((kpi) => (
          <Card key={kpi.label}>
            <div className={styles.kpi}>
              <span className={styles.kpiLabel}>{kpi.label}</span>
              <span className={styles.kpiValue}>{kpi.value}</span>
              <span className={styles.kpiSub}>{kpi.sub}</span>
            </div>
          </Card>
        ))}
      </div>

      <div className={styles.charts}>
        <Card>
          <p className={styles.chartTitle}>Calls — last 30 days</p>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={byDay ?? []} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="callGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="date" tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 11 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ background: "var(--color-bg-elevated)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: "var(--color-text-secondary)" }}
                itemStyle={{ color: "var(--color-accent-hover)" }}
              />
              <Area type="monotone" dataKey="calls" stroke="#6366f1" strokeWidth={2} fill="url(#callGrad)" dot={false} activeDot={{ r: 4, fill: "#818cf8" }} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <p className={styles.chartTitle}>By provider</p>
          <div className={styles.providerList}>
            {byProvider && byProvider.length > 0 ? (
              byProvider.map((p) => (
                <div key={p.provider} className={styles.providerRow}>
                  <span className={styles.providerName}>{p.provider}</span>
                  <div className={styles.providerBar}>
                    <div className={styles.providerBarFill} style={{ width: `${(p.calls / maxCalls) * 100}%` }} />
                  </div>
                  <span className={styles.providerCalls}>{p.calls}</span>
                </div>
              ))
            ) : (
              <p className={styles.empty}>No data yet</p>
            )}
          </div>
        </Card>
      </div>

      {wsStatus && (
        <Card>
          <p className={styles.chartTitle}>Provider status</p>
          <div className={styles.statusGrid}>
            {wsStatus.providers.map((p) => (
              <div key={p.slug} className={styles.statusCard}>
                <span className={styles.statusName}>{p.provider}</span>
                <div className={styles.statusDots}>
                  {Array.from({ length: p.active_keys }).map((_, i) => (
                    <div key={`a${i}`} className={`${styles.dot} ${styles.dotActive}`} title="Active" />
                  ))}
                  {Array.from({ length: p.exhausted_keys }).map((_, i) => (
                    <div key={`e${i}`} className={`${styles.dot} ${styles.dotExhausted}`} title="Rate-limited" />
                  ))}
                  {Array.from({ length: p.disabled_keys }).map((_, i) => (
                    <div key={`d${i}`} className={`${styles.dot} ${styles.dotDisabled}`} title="Disabled" />
                  ))}
                  {p.total_keys === 0 && <span className={styles.empty}>No keys</span>}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
