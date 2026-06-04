import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listKeys, createKey, deleteKey, testKey, updateKey, type ApiKeyCreate } from "../api/keys";
import { listProviders, createProvider } from "../api/providers";
import { detectProviderSlug } from "../utils/keyDetect";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";

const INITIAL_FORM: ApiKeyCreate = { provider_id: "", name: "", api_key_plaintext: "", tier: "free" };

function getErrorMessage(err: unknown): string {
  if (err && typeof err === "object" && "response" in err) {
    const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (detail) return String(detail);
  }
  if (err instanceof Error) return err.message;
  return "An unexpected error occurred";
}

export default function ApiKeys() {
  const qc = useQueryClient();
  const { data: keys = [] } = useQuery({ queryKey: ["keys"], queryFn: listKeys });
  const { data: providers = [] } = useQuery({ queryKey: ["providers"], queryFn: listProviders });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<ApiKeyCreate>(INITIAL_FORM);
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; latency_ms: number; error?: string }>>({});
  const [customOpen, setCustomOpen] = useState(false);
  const [customForm, setCustomForm] = useState({ name: "", api_base_url: "" });
  const [detectedSlug, setDetectedSlug] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const createMut = useMutation({
    mutationFn: createKey,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["keys"] });
      setOpen(false);
      setForm(INITIAL_FORM);
      setDetectedSlug(null);
      setFormError(null);
    },
    onError: (err: unknown) => setFormError(getErrorMessage(err)),
  });

  const deleteMut = useMutation({
    mutationFn: deleteKey,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["keys"] }),
    onError: (err: unknown) => setActionError(getErrorMessage(err)),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => updateKey(id, { is_enabled: enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["keys"] }),
    onError: (err: unknown) => setActionError(getErrorMessage(err)),
  });

  const createProviderMut = useMutation({
    mutationFn: createProvider,
    onSuccess: (newProvider) => {
      qc.invalidateQueries({ queryKey: ["providers"] });
      setForm((f) => ({ ...f, provider_id: newProvider.id }));
      setCustomOpen(false);
      setCustomForm({ name: "", api_base_url: "" });
    },
    onError: (err: unknown) => setFormError(getErrorMessage(err)),
  });

  const handleKeyChange = (value: string) => {
    setForm((f) => ({ ...f, api_key_plaintext: value }));
    const slug = detectProviderSlug(value);
    setDetectedSlug(slug);
    if (slug) {
      const matched = providers.find((p) => p.slug === slug);
      if (matched) setForm((f) => ({ ...f, provider_id: matched.id }));
    }
  };

  const handleTest = async (id: string) => {
    try {
      const result = await testKey(id);
      setTestResults((prev) => ({ ...prev, [id]: result }));
    } catch (err) {
      setActionError(getErrorMessage(err));
    }
  };

  const handleClose = () => {
    setOpen(false);
    setForm(INITIAL_FORM);
    setDetectedSlug(null);
    setFormError(null);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: "var(--weight-bold)", letterSpacing: "-0.02em" }}>API Keys</h1>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginTop: "var(--space-1)" }}>Provider keys — stored encrypted, never exposed in plain text</p>
        </div>
        <Button onClick={() => setOpen(true)}>+ Add key</Button>
      </div>

      {actionError && (
        <div style={{ padding: "var(--space-3) var(--space-4)", background: "var(--color-error-dim, rgba(239,68,68,0.1))", border: "1px solid var(--color-error)", borderRadius: "var(--radius-md)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "var(--space-3)" }}>
          <span style={{ fontSize: "var(--text-sm)", color: "var(--color-error)" }}>{actionError}</span>
          <button type="button" onClick={() => setActionError(null)} style={{ background: "none", border: "none", color: "var(--color-error)", cursor: "pointer", fontSize: "var(--text-sm)", padding: 0, lineHeight: 1 }}>✕</button>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
        {keys.length === 0 && (
          <Card><p style={{ color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>No API keys yet. Add one to start routing requests.</p></Card>
        )}
        {keys.map((k) => {
          const tr = testResults[k.id];
          return (
            <Card key={k.id}>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)", flexWrap: "wrap" }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-1)" }}>
                    <span style={{ fontWeight: "var(--weight-semibold)", fontSize: "var(--text-sm)" }}>{k.name}</span>
                    <Badge variant={k.tier === "paid" ? "warning" : "success"}>{k.tier}</Badge>
                    <Badge variant={k.is_enabled ? "success" : "error"}>{k.is_enabled ? "active" : "disabled"}</Badge>
                  </div>
                  <code style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>{k.key_masked}</code>
                  <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginLeft: "var(--space-4)" }}>{k.provider_slug}</span>
                  {k.rate_limit_rpm && <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginLeft: "var(--space-2)" }}>·{k.rate_limit_rpm}/h</span>}
                  {k.rate_limit_rpd && <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginLeft: "var(--space-2)" }}>·{k.rate_limit_rpd}/d</span>}
                </div>
                <div style={{ display: "flex", gap: "var(--space-2)", flexShrink: 0 }}>
                  {tr && (
                    <span style={{ fontSize: "var(--text-xs)", color: tr.ok ? "var(--color-success)" : "var(--color-error)", alignSelf: "center" }}>
                      {tr.ok ? `✓ ${tr.latency_ms}ms` : `✗ ${tr.error ?? "error"}`}
                    </span>
                  )}
                  <Button variant="ghost" size="sm" onClick={() => handleTest(k.id)}>Test</Button>
                  <Button variant="ghost" size="sm" onClick={() => toggleMut.mutate({ id: k.id, enabled: !k.is_enabled })}>
                    {k.is_enabled ? "Disable" : "Enable"}
                  </Button>
                  <Button variant="danger" size="sm" onClick={() => { if (confirm("Delete this key?")) deleteMut.mutate(k.id); }}>Delete</Button>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      <Modal open={open} onClose={handleClose} title="Add API key">
        <form onSubmit={(e) => { e.preventDefault(); createMut.mutate(form); }} style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <div>
            <label style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", fontWeight: "var(--weight-medium)", display: "block", marginBottom: "var(--space-1)" }}>Provider</label>
            <select
              value={form.provider_id}
              onChange={(e) => setForm((f) => ({ ...f, provider_id: e.target.value }))}
              required
              style={{ width: "100%", background: "var(--color-bg-elevated)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "var(--space-2) var(--space-3)", color: "var(--color-text-primary)", fontSize: "var(--text-sm)" }}
            >
              <option value="">— Select —</option>
              {providers.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-1)" }}>
              Provider not listed?{" "}
              <button
                type="button"
                onClick={() => setCustomOpen(true)}
                style={{ background: "none", border: "none", color: "var(--color-accent)", cursor: "pointer", fontSize: "inherit", padding: 0, textDecoration: "underline" }}
              >
                Add custom
              </button>
            </p>
          </div>
          <Input label="Name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required placeholder="e.g. Personal GROQ key" />
          <div>
            <Input
              label="API key"
              type="password"
              value={form.api_key_plaintext}
              onChange={(e) => handleKeyChange(e.target.value)}
              required
              placeholder="sk-... / nvapi-... / gsk_..."
              autoComplete="off"
            />
            {detectedSlug && (
              <p style={{ fontSize: "var(--text-xs)", color: "var(--color-success)", marginTop: "var(--space-1)" }}>
                Detected: {providers.find((p) => p.slug === detectedSlug)?.name ?? detectedSlug}
              </p>
            )}
          </div>
          <div style={{ display: "flex", gap: "var(--space-3)" }}>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", fontWeight: "var(--weight-medium)", display: "block", marginBottom: "var(--space-1)" }}>Tier</label>
              <select value={form.tier} onChange={(e) => setForm((f) => ({ ...f, tier: e.target.value }))} style={{ width: "100%", background: "var(--color-bg-elevated)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "var(--space-2) var(--space-3)", color: "var(--color-text-primary)", fontSize: "var(--text-sm)" }}>
                <option value="free">Free</option>
                <option value="paid">Paid</option>
              </select>
            </div>
            <Input
              label="Limit calls/hour"
              type="number"
              value={form.rate_limit_rpm ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, rate_limit_rpm: e.target.value ? Number(e.target.value) : undefined }))}
              placeholder="e.g. 60"
              style={{ flex: 1 }}
            />
            <Input
              label="Limit calls/day"
              type="number"
              value={form.rate_limit_rpd ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, rate_limit_rpd: e.target.value ? Number(e.target.value) : undefined }))}
              placeholder="e.g. 1000"
              style={{ flex: 1 }}
            />
          </div>
          <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "flex-end", marginTop: "var(--space-2)" }}>
            {formError && (
              <p style={{ flex: 1, fontSize: "var(--text-xs)", color: "var(--color-error)", alignSelf: "center" }}>{formError}</p>
            )}
            <Button variant="secondary" type="button" onClick={handleClose}>Cancel</Button>
            <Button type="submit" loading={createMut.isPending}>Save</Button>
          </div>
        </form>
      </Modal>
      <Modal open={customOpen} onClose={() => setCustomOpen(false)} title="Add custom provider">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createProviderMut.mutate({ ...customForm, protocol: "openai" });
          }}
          style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}
        >
          <Input
            label="Provider name"
            value={customForm.name}
            onChange={(e) => setCustomForm((f) => ({ ...f, name: e.target.value }))}
            required
            placeholder="e.g. DeepSeek, Cerebras, xAI"
          />
          <Input
            label="Base URL"
            value={customForm.api_base_url}
            onChange={(e) => setCustomForm((f) => ({ ...f, api_base_url: e.target.value }))}
            required
            placeholder="https://api.deepseek.com/v1"
          />
          <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
            Works with any OpenAI-compatible API. The provider will appear in the list immediately.
          </p>
          <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "flex-end" }}>
            <Button variant="secondary" type="button" onClick={() => setCustomOpen(false)}>Cancel</Button>
            <Button type="submit" loading={createProviderMut.isPending}>Add provider</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
