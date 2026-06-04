import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listModels, refreshModels, setModelEnabled } from '../api/models';
import type { ModelCatalogItem } from '../api/models';
import { listProviders } from '../api/providers';
import type { Provider } from '../api/providers';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import styles from './Models.module.css';

const ONE_DAY_MS = 24 * 60 * 60 * 1000;

type TierFilter = 'all' | 'free' | 'paid';

function isNew(lastDiscoveredAt: string): boolean {
  return Date.now() - new Date(lastDiscoveredAt).getTime() < ONE_DAY_MS;
}

function formatContextWindow(ctx: number | null): string {
  if (ctx === null) return '—';
  if (ctx >= 1_000_000) return (ctx / 1_000_000).toFixed(0) + 'M';
  if (ctx >= 1_000) return (ctx / 1_000).toFixed(0) + 'K';
  return ctx.toString();
}

function formatCost(value: string | null): string {
  if (value === null) return '—';
  const n = parseFloat(value);
  if (n === 0) return 'free';
  return '$' + n.toFixed(4);
}

export default function Models() {
  const queryClient = useQueryClient();
  const [providerFilter, setProviderFilter] = useState('');
  const [tierFilter, setTierFilter] = useState<TierFilter>('all');
  const [activeOnly, setActiveOnly] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState<string | null>(null);

  const { data: providers } = useQuery<Provider[]>({
    queryKey: ['providers'],
    queryFn: listProviders,
  });

  const { data: models, isLoading } = useQuery<ModelCatalogItem[]>({
    queryKey: ['models', providerFilter, tierFilter, activeOnly],
    queryFn: () =>
      listModels({
        provider: providerFilter || undefined,
        tier: tierFilter !== 'all' ? tierFilter : undefined,
        active: activeOnly || undefined,
      }),
    refetchInterval: 60_000,
  });

  const refreshMutation = useMutation({
    mutationFn: refreshModels,
    onSuccess: (res) => {
      setRefreshMsg(res.message);
      void queryClient.invalidateQueries({ queryKey: ['models'] });
      setTimeout(() => setRefreshMsg(null), 4000);
    },
    onError: () => {
      setRefreshMsg('Refresh failed');
      setTimeout(() => setRefreshMsg(null), 4000);
    },
  });

  const enabledMutation = useMutation({
    mutationFn: ({ id, isEnabled }: { id: string; isEnabled: boolean }) =>
      setModelEnabled(id, isEnabled),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['models'] });
    },
  });

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.heading}>
          <h1 className={styles.title}>Models</h1>
          <p className={styles.subtitle}>Catalog of all discovered models across providers</p>
        </div>
        <div className={styles.headerActions}>
          {refreshMsg && <span className={styles.refreshMsg}>{refreshMsg}</span>}
          <Button
            variant="secondary"
            size="sm"
            loading={refreshMutation.isPending}
            onClick={() => refreshMutation.mutate()}
          >
            Refresh now
          </Button>
        </div>
      </div>

      <Card className={styles.filtersCard}>
        <div className={styles.filters}>
          <div className={styles.filterGroup}>
            <label className={styles.filterLabel} htmlFor="provider-filter">Provider</label>
            <select
              id="provider-filter"
              className={styles.select}
              value={providerFilter}
              onChange={(e) => setProviderFilter(e.target.value)}
            >
              <option value="">All providers</option>
              {providers?.map((p: Provider) => (
                <option key={p.id} value={p.slug}>{p.name}</option>
              ))}
            </select>
          </div>

          <div className={styles.filterGroup}>
            <label className={styles.filterLabel} htmlFor="tier-filter">Tier</label>
            <select
              id="tier-filter"
              className={styles.select}
              value={tierFilter}
              onChange={(e) => setTierFilter(e.target.value as TierFilter)}
            >
              <option value="all">All tiers</option>
              <option value="free">Free</option>
              <option value="paid">Paid</option>
            </select>
          </div>

          <label className={styles.toggleLabel}>
            <input
              type="checkbox"
              className={styles.checkbox}
              checked={activeOnly}
              onChange={(e) => setActiveOnly(e.target.checked)}
            />
            <span>Active only</span>
          </label>
        </div>
      </Card>

      <Card>
        {isLoading ? (
          <p className={styles.empty}>Loading models...</p>
        ) : models && models.length > 0 ? (
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Model ID</th>
                  <th>Display name</th>
                  <th>Tier</th>
                  <th className={styles.numCol}>Context</th>
                  <th className={styles.numCol}>Cost in / out</th>
                  <th className={styles.iconCol}>Vision</th>
                  <th className={styles.iconCol}>Tools</th>
                  <th className={styles.iconCol}>Active</th>
                  <th className={styles.iconCol}>Enabled</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {models.map((m: ModelCatalogItem) => (
                  <tr key={m.id} className={!m.is_active ? styles.rowInactive : undefined}>
                    <td className={styles.providerCell}>{m.provider_slug}</td>
                    <td>
                      <div className={styles.modelIdCell}>
                        <span className={styles.modelId}>{m.model_id}</span>
                        {m.is_default && (
                          <span className={styles.defaultBadge}>DEFAULT</span>
                        )}
                        {isNew(m.last_discovered_at) && (
                          <span className={styles.newBadge}>NEW</span>
                        )}
                      </div>
                    </td>
                    <td className={styles.displayName}>{m.display_name}</td>
                    <td>
                      <span className={m.tier === 'free' ? styles.tierFree : styles.tierPaid}>
                        {m.tier.toUpperCase()}
                      </span>
                    </td>
                    <td className={styles.numCol}>{formatContextWindow(m.context_window)}</td>
                    <td className={styles.numCol}>
                      <span className={styles.costPair}>
                        <span>{formatCost(m.cost_input_per_1m_usd)}</span>
                        <span className={styles.costSep}>/</span>
                        <span>{formatCost(m.cost_output_per_1m_usd)}</span>
                      </span>
                    </td>
                    <td className={styles.iconCol}>
                      <span className={m.supports_vision ? styles.checkOn : styles.checkOff}>
                        {m.supports_vision ? '✓' : '—'}
                      </span>
                    </td>
                    <td className={styles.iconCol}>
                      <span className={m.supports_tools ? styles.checkOn : styles.checkOff}>
                        {m.supports_tools ? '✓' : '—'}
                      </span>
                    </td>
                    <td className={styles.iconCol}>
                      <span className={m.is_active ? styles.checkOn : styles.checkOff}>
                        {m.is_active ? '✓' : '✗'}
                      </span>
                    </td>
                    <td className={styles.iconCol}>
                      <input
                        type="checkbox"
                        className={styles.checkbox}
                        checked={m.is_enabled}
                        disabled={enabledMutation.isPending}
                        title={m.is_enabled ? 'Disable model' : 'Enable model'}
                        onChange={(e) =>
                          enabledMutation.mutate({ id: m.id, isEnabled: e.target.checked })
                        }
                      />
                    </td>
                    <td className={styles.dateCell}>
                      {new Date(m.last_discovered_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className={styles.empty}>No models found</p>
        )}
      </Card>
    </div>
  );
}
