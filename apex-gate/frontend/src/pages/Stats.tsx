import { useQuery } from '@tanstack/react-query';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from 'recharts';
import { fetchByDay, fetchByProvider, fetchByModel, fetchCosts } from '../api/stats';
import type { ProviderStat, ModelStat, DayStat, CostStat } from '../api/stats';
import { Card } from '../components/ui/Card';
import styles from './Stats.module.css';

const PIE_COLORS = ['#6366f1', '#a78bfa', '#34d399', '#fbbf24', '#f87171', '#38bdf8', '#fb923c', '#e879f9'];

interface TooltipPayloadItem {
  name: string;
  value: number | string;
  color?: string;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}

function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className={styles.tooltip}>
      {label && <p className={styles.tooltipLabel}>{label}</p>}
      {payload.map((item) => (
        <p key={item.name} className={styles.tooltipRow} style={{ color: item.color ?? 'var(--color-text-primary)' }}>
          <span>{item.name}:</span> <strong>{item.value}</strong>
        </p>
      ))}
    </div>
  );
}

type ProviderStatExtended = ProviderStat & { rate_limits?: number };

function buildCumulativeCosts(costs: CostStat[]): { name: string; cumulative: number }[] {
  const sorted = [...costs].sort((a, b) => parseFloat(a.total_cost) - parseFloat(b.total_cost));
  let running = 0;
  return sorted.map((c) => {
    running += parseFloat(c.total_cost);
    return { name: c.key_name, cumulative: parseFloat(running.toFixed(4)) };
  });
}

export default function Stats() {
  const { data: byDay } = useQuery<DayStat[]>({ queryKey: ['byDay'], queryFn: fetchByDay, refetchInterval: 60_000 });
  const { data: byProvider } = useQuery<ProviderStat[]>({ queryKey: ['byProvider'], queryFn: fetchByProvider, refetchInterval: 60_000 });
  const { data: byModel } = useQuery<ModelStat[]>({ queryKey: ['byModel'], queryFn: fetchByModel, refetchInterval: 60_000 });
  const { data: costs } = useQuery<CostStat[]>({ queryKey: ['costs'], queryFn: fetchCosts, refetchInterval: 120_000 });

  const hasCosts = Boolean(costs && costs.length > 0 && costs.some((c) => parseFloat(c.total_cost) > 0));
  const cumulativeCosts = hasCosts && costs ? buildCumulativeCosts(costs) : [];
  const pieData = byProvider?.map((p) => ({ name: p.provider, value: p.calls })) ?? [];

  return (
    <div className={styles.page}>
      <div className={styles.heading}>
        <h1 className={styles.title}>Statistics</h1>
        <p className={styles.subtitle}>Detailed usage metrics across all providers and models</p>
      </div>

      <div className={styles.chartsGrid}>
        <Card className={styles.chartCard}>
          <p className={styles.chartTitle}>Calls per day — last 30 days</p>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={byDay ?? []} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="callsGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Area
                type="monotone"
                dataKey="calls"
                name="Calls"
                stroke="#6366f1"
                strokeWidth={2}
                fill="url(#callsGrad)"
                dot={false}
                activeDot={{ r: 4, fill: '#818cf8' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card className={styles.chartCard}>
          <p className={styles.chartTitle}>Distribution by provider</p>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={85}
                paddingAngle={3}
                dataKey="value"
              >
                {pieData.map((_entry, idx) => (
                  <Cell key={`cell-${idx}`} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<ChartTooltip />} />
              <Legend
                formatter={(value: string) => (
                  <span style={{ color: 'rgba(255,255,255,0.55)', fontSize: 12 }}>{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card className={styles.chartCard}>
          <p className={styles.chartTitle}>Avg latency per model (ms)</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={byModel ?? []} margin={{ top: 4, right: 4, left: -20, bottom: 40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="model_id"
                tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                interval={0}
                angle={-30}
                textAnchor="end"
                height={52}
              />
              <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="avg_latency_ms" name="Avg latency (ms)" fill="#a78bfa" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {hasCosts && (
          <Card className={styles.chartCard}>
            <p className={styles.chartTitle}>Cumulative cost (USD)</p>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={cumulativeCosts} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#fbbf24" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#fbbf24" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis
                  dataKey="name"
                  tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  interval={0}
                  angle={-30}
                  textAnchor="end"
                  height={52}
                />
                <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} tickLine={false} axisLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <Area
                  type="monotone"
                  dataKey="cumulative"
                  name="Cost (USD)"
                  stroke="#fbbf24"
                  strokeWidth={2}
                  fill="url(#costGrad)"
                  dot={false}
                  activeDot={{ r: 4, fill: '#fbbf24' }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        )}
      </div>

      <Card>
        <p className={styles.chartTitle}>Provider summary</p>
        {byProvider && byProvider.length > 0 ? (
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Provider</th>
                  <th className={styles.numCol}>Calls</th>
                  <th className={styles.numCol}>Rate limits</th>
                  <th className={styles.numCol}>Total cost</th>
                </tr>
              </thead>
              <tbody>
                {byProvider.map((p: ProviderStatExtended) => (
                  <tr key={p.provider}>
                    <td className={styles.providerCell}>{p.provider}</td>
                    <td className={styles.numCol}>{p.calls.toLocaleString()}</td>
                    <td className={styles.numCol}>
                      <span className={styles.rateLimitBadge}>{p.rate_limits ?? 0}</span>
                    </td>
                    <td className={styles.numCol}>
                      {parseFloat(p.cost) > 0 ? (
                        <span className={styles.costValue}>${parseFloat(p.cost).toFixed(4)}</span>
                      ) : (
                        <span className={styles.freeBadge}>free</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className={styles.empty}>No provider data yet</p>
        )}
      </Card>
    </div>
  );
}
