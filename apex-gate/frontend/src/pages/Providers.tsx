import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listProviders, getProviderModels } from "../api/providers";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";

export default function Providers() {
  const { data: providers = [] } = useQuery({ queryKey: ["providers"], queryFn: listProviders });
  const [expanded, setExpanded] = useState<string | null>(null);
  const { data: models = [] } = useQuery({
    queryKey: ["providerModels", expanded],
    queryFn: () => getProviderModels(expanded!),
    enabled: !!expanded,
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      <div>
        <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: "var(--weight-bold)", letterSpacing: "-0.02em" }}>Providers</h1>
        <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginTop: "var(--space-1)" }}>Supported LLM providers and their available models</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "var(--space-4)" }}>
        {providers.map((p) => (
          <Card key={p.id} style={{ cursor: "pointer" }} onClick={() => setExpanded(expanded === p.slug ? null : p.slug)}>
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "var(--space-3)" }}>
              <div>
                <div style={{ fontWeight: "var(--weight-semibold)", fontSize: "var(--text-sm)", marginBottom: "var(--space-1)" }}>{p.name}</div>
                <code style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>{p.slug}</code>
              </div>
              <div style={{ display: "flex", gap: "var(--space-1)", flexDirection: "column", alignItems: "flex-end" }}>
                <Badge variant={p.supports_free_tier ? "success" : "neutral"}>{p.supports_free_tier ? "free tier" : "paid"}</Badge>
                <Badge variant="info">{p.protocol}</Badge>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>{p.key_count} key{p.key_count !== 1 ? "s" : ""} configured</span>
              <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); setExpanded(expanded === p.slug ? null : p.slug); }}>
                {expanded === p.slug ? "Hide models" : "View models"}
              </Button>
            </div>

            {expanded === p.slug && models.length > 0 && (
              <div style={{ marginTop: "var(--space-4)", borderTop: "1px solid var(--color-border)", paddingTop: "var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
                {models.map((m) => (
                  <div key={m.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <code style={{ fontSize: "var(--text-xs)", color: "var(--color-text-secondary)", fontFamily: "var(--font-mono)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {m.model_id}
                    </code>
                    <div style={{ display: "flex", gap: "var(--space-1)", marginLeft: "var(--space-2)", flexShrink: 0 }}>
                      <Badge variant={m.tier === "paid" ? "warning" : "success"}>{m.tier}</Badge>
                      {!m.is_active && <Badge variant="error">inactive</Badge>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
