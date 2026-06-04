import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listVirtualKeys, createVirtualKey, rotateVirtualKey, deleteVirtualKey, updateVirtualKey } from "../api/virtualKeys";
import type { MemoryMode } from "../api/virtualKeys";

const CHAT_VK_KEY = "apex-chat-virtual-key";
const CHAT_KEYS_MAP = "apex-chat-keys";

function saveKeyForChat(id: string, plaintext: string): void {
  localStorage.setItem(CHAT_VK_KEY, plaintext);
  try {
    const map: Record<string, string> = JSON.parse(localStorage.getItem(CHAT_KEYS_MAP) ?? "{}");
    map[id] = plaintext;
    localStorage.setItem(CHAT_KEYS_MAP, JSON.stringify(map));
  } catch { /* ignore */ }
}
import { listKeys } from "../api/keys";
import type { ApiKey } from "../api/keys";
import { listModels } from "../api/models";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";

type RoutingMode = "auto" | "explicit";

/** Base URL where the APEX GATE proxy endpoints are served.
 *  In dev the FastAPI backend listens on :8000; override via VITE_PROXY_BASE_URL in prod. */
const PROXY_BASE_URL: string =
  (import.meta.env.VITE_PROXY_BASE_URL as string | undefined) ?? "http://localhost:8000";

interface Revealed {
  id: string;
  key: string;
}

interface Assignment {
  api_key_id: string;
  priority: number;
  name: string;
  provider_slug: string;
}

function getErrorMessage(err: unknown): string {
  if (err && typeof err === "object" && "response" in err) {
    const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (detail) return String(detail);
  }
  if (err instanceof Error) return err.message;
  return "An unexpected error occurred";
}

interface EndpointDoc {
  label: string;
  method: string;
  path: string;
  example: string;
}

function buildEndpointDocs(): EndpointDoc[] {
  const base = PROXY_BASE_URL;
  return [
    {
      label: "OpenAI",
      method: "POST",
      path: "/v1/chat/completions",
      example: `curl ${base}/v1/chat/completions \\
  -H "Authorization: Bearer YOUR_APG_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"model":"auto","messages":[{"role":"user","content":"Ciao"}]}'`,
    },
    {
      label: "Anthropic",
      method: "POST",
      path: "/anthropic/v1/messages",
      example: `curl ${base}/anthropic/v1/messages \\
  -H "Authorization: Bearer YOUR_APG_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"model":"auto","max_tokens":256,"messages":[{"role":"user","content":"Ciao"}]}'`,
    },
    {
      label: "Gemini",
      method: "POST",
      path: "/gemini/v1/generateContent",
      example: `curl ${base}/gemini/v1/generateContent \\
  -H "Authorization: Bearer YOUR_APG_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"contents":[{"role":"user","parts":[{"text":"Ciao"}]}]}'`,
    },
    {
      label: "Ollama",
      method: "POST",
      path: "/api/chat",
      example: `curl ${base}/api/chat \\
  -H "Authorization: Bearer YOUR_APG_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"model":"auto","stream":false,"messages":[{"role":"user","content":"Ciao"}]}'`,
    },
  ];
}

function UsagePanel({ keyPrefix }: { keyPrefix: string }) {
  const docs = buildEndpointDocs();
  return (
    <div style={{ marginTop: "var(--space-4)", paddingTop: "var(--space-4)", borderTop: "1px solid var(--color-border)", display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", lineHeight: 1.5 }}>
        Il <strong>formato di output</strong> dipende dall'endpoint che chiami. Usa la tua chiave completa{" "}
        <code style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent-hover)" }}>{keyPrefix}…</code>{" "}
        al posto di <code style={{ fontFamily: "var(--font-mono)" }}>YOUR_APG_KEY</code>. Lascia{" "}
        <code style={{ fontFamily: "var(--font-mono)" }}>model:"auto"</code> per usare il routing/preferenza della key.
      </p>
      {docs.map((d) => (
        <div key={d.label}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-2)" }}>
            <Badge variant="info">{d.label}</Badge>
            <code style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", color: "var(--color-text-secondary)" }}>
              {d.method} {PROXY_BASE_URL}{d.path}
            </code>
          </div>
          <pre style={{ margin: 0, fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", background: "var(--color-bg-overlay)", padding: "var(--space-3)", borderRadius: "var(--radius-md)", overflowX: "auto", color: "var(--color-text-primary)", lineHeight: 1.5 }}>
            {d.example}
          </pre>
        </div>
      ))}
    </div>
  );
}

export default function VirtualKeys() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: vkeys = [] } = useQuery({ queryKey: ["vkeys"], queryFn: listVirtualKeys });
  const { data: keys = [] } = useQuery({ queryKey: ["keys"], queryFn: listKeys });
  const { data: models = [] } = useQuery({ queryKey: ["models", "active", "enabled"], queryFn: () => listModels({ active: true, enabled: true }) });
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [budget, setBudget] = useState<string>("");
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [revealed, setRevealed] = useState<Revealed | null>(null);
  const [routingMode, setRoutingMode] = useState<RoutingMode>("auto");
  const [modelPref, setModelPref] = useState("");
  const [memoryMode, setMemoryMode] = useState<MemoryMode>("off");
  const [formError, setFormError] = useState<string | null>(null);
  const [usagePanelId, setUsagePanelId] = useState<string | null>(null);

  // Only offer models from providers whose keys are assigned (or all when none selected yet).
  const assignedSlugs = new Set(assignments.map((a) => a.provider_slug).filter(Boolean));
  const selectableModels = assignedSlugs.size > 0
    ? models.filter((m) => assignedSlugs.has(m.provider_slug))
    : models;

  const toggleKey = (key: ApiKey) => {
    setAssignments((prev) => {
      const exists = prev.find((a) => a.api_key_id === key.id);
      if (exists) return prev.filter((a) => a.api_key_id !== key.id);
      return [...prev, { api_key_id: key.id, priority: 10, name: key.name, provider_slug: key.provider_slug ?? "" }];
    });
  };

  const resetForm = () => {
    setName("");
    setBudget("");
    setAssignments([]);
    setRoutingMode("auto");
    setModelPref("");
    setMemoryMode("off");
  };

  const createMut = useMutation({
    mutationFn: () => createVirtualKey({
      name,
      daily_token_budget: budget ? Number(budget) : undefined,
      assignments: assignments.map((a) => ({ api_key_id: a.api_key_id, priority: a.priority })),
      model_preference: routingMode === "explicit" && modelPref.trim() ? modelPref.trim() : null,
      memory_mode: memoryMode,
    }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["vkeys"] });
      setOpen(false);
      resetForm();
      setFormError(null);
      setRevealed({ id: data.id, key: data.key_plaintext });
    },
    onError: (err: unknown) => setFormError(getErrorMessage(err)),
  });

  const rotateMut = useMutation({
    mutationFn: rotateVirtualKey,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["vkeys"] });
      setRevealed({ id: data.id, key: data.key_plaintext });
    },
    onError: (err: unknown) => setFormError(getErrorMessage(err)),
  });

  const deleteMut = useMutation({
    mutationFn: deleteVirtualKey,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vkeys"] }),
    onError: (err: unknown) => setFormError(getErrorMessage(err)),
  });

  const memoryMut = useMutation({
    mutationFn: ({ id, mode }: { id: string; mode: MemoryMode }) => updateVirtualKey(id, { memory_mode: mode }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vkeys"] }),
    onError: (err: unknown) => setFormError(getErrorMessage(err)),
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: "var(--weight-bold)", letterSpacing: "-0.02em" }}>Virtual Keys</h1>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginTop: "var(--space-1)" }}>
            Distribute <code style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent-hover)" }}>apg-…</code> keys to your applications
          </p>
        </div>
        <Button onClick={() => setOpen(true)}>+ Create key</Button>
      </div>

      {revealed && (
        <Card glow>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--color-success)", marginBottom: "var(--space-3)", fontWeight: "var(--weight-semibold)" }}>
            ✓ Key generated — copy it now, it won't be shown again
          </p>
          <code style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-sm)", background: "var(--color-bg-overlay)", padding: "var(--space-3) var(--space-4)", borderRadius: "var(--radius-md)", display: "block", wordBreak: "break-all", color: "var(--color-text-primary)" }}>
            {revealed.key}
          </code>
          <div style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-3)", flexWrap: "wrap" }}>
            <Button variant="ghost" size="sm" onClick={() => { navigator.clipboard.writeText(revealed.key); }}>Copia</Button>
            <Button size="sm" onClick={() => { saveKeyForChat(revealed.id, revealed.key); navigate("/chat"); }}>Usa in Chat →</Button>
            <Button variant="ghost" size="sm" onClick={() => setRevealed(null)}>Chiudi</Button>
          </div>
        </Card>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
        {vkeys.length === 0 && (
          <Card><p style={{ color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>No virtual keys yet.</p></Card>
        )}
        {vkeys.map((vk) => (
          <Card key={vk.id}>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)", flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-1)" }}>
                  <span style={{ fontWeight: "var(--weight-semibold)", fontSize: "var(--text-sm)" }}>{vk.name}</span>
                  <Badge variant={vk.is_enabled ? "success" : "error"}>{vk.is_enabled ? "active" : "disabled"}</Badge>
                  {vk.model_preference ? (
                    <Badge variant="info">explicit: {vk.model_preference}</Badge>
                  ) : (
                    <Badge variant="neutral">auto</Badge>
                  )}
                  <Badge variant={vk.memory_mode === "off" ? "neutral" : "success"}>
                    memory: {vk.memory_mode}
                  </Badge>
                </div>
                <code style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>{vk.key_prefix}…</code>
                {vk.daily_token_budget && (
                  <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginLeft: "var(--space-4)" }}>
                    Budget: {vk.daily_token_budget.toLocaleString()} tokens/day
                  </span>
                )}
                {vk.assignments && vk.assignments.length > 0 && (
                  <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginLeft: "var(--space-4)" }}>
                    Keys: {vk.assignments.map((a) => `${a.key_name ?? a.api_key_id} (p${a.priority})`).join(", ")}
                  </span>
                )}
              </div>
              <div style={{ display: "flex", gap: "var(--space-2)", flexShrink: 0, alignItems: "center" }}>
                <select
                  aria-label="Memory mode"
                  value={vk.memory_mode}
                  onChange={(e) => memoryMut.mutate({ id: vk.id, mode: e.target.value as MemoryMode })}
                  disabled={memoryMut.isPending}
                  title="Server-side conversation memory for this key"
                  style={{
                    background: "var(--color-bg-elevated)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-md)",
                    padding: "var(--space-1) var(--space-2)",
                    color: "var(--color-text-primary)",
                    fontSize: "var(--text-xs)",
                    cursor: "pointer",
                  }}
                >
                  <option value="off">mem: off</option>
                  <option value="optional">mem: optional</option>
                  <option value="always">mem: always</option>
                </select>
                <Button variant="ghost" size="sm" onClick={() => setUsagePanelId(usagePanelId === vk.id ? null : vk.id)}>
                  {usagePanelId === vk.id ? "Hide usage" : "Usage"}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => rotateMut.mutate(vk.id)}>Rotate</Button>
                <Button variant="danger" size="sm" onClick={() => { if (confirm("Delete this virtual key?")) deleteMut.mutate(vk.id); }}>Delete</Button>
              </div>
            </div>
            {usagePanelId === vk.id && <UsagePanel keyPrefix={vk.key_prefix} />}
          </Card>
        ))}
      </div>

      <Modal open={open} onClose={() => { setOpen(false); resetForm(); }} title="Create virtual key">
        <form onSubmit={(e) => { e.preventDefault(); createMut.mutate(); }} style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} required placeholder="e.g. Production app" />
          <Input label="Daily token budget (optional)" type="number" value={budget} onChange={(e) => setBudget(e.target.value)} placeholder="Leave empty for unlimited" />

          <div>
            <label style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", fontWeight: "var(--weight-medium)", display: "block", marginBottom: "var(--space-2)" }}>
              Model routing
            </label>
            <div style={{ display: "flex", gap: "var(--space-2)", marginBottom: "var(--space-3)" }}>
              <button
                type="button"
                onClick={() => setRoutingMode("auto")}
                style={{
                  padding: "var(--space-2) var(--space-4)",
                  borderRadius: "var(--radius-md)",
                  border: `1px solid ${routingMode === "auto" ? "var(--color-accent)" : "var(--color-border)"}`,
                  background: routingMode === "auto" ? "var(--color-accent-dim)" : "var(--color-bg-elevated)",
                  color: routingMode === "auto" ? "var(--color-accent-hover)" : "var(--color-text-secondary)",
                  fontWeight: routingMode === "auto" ? "var(--weight-semibold)" : "var(--weight-normal)",
                  fontSize: "var(--text-sm)",
                  cursor: "pointer",
                }}
              >
                AUTO
              </button>
              <button
                type="button"
                onClick={() => setRoutingMode("explicit")}
                style={{
                  padding: "var(--space-2) var(--space-4)",
                  borderRadius: "var(--radius-md)",
                  border: `1px solid ${routingMode === "explicit" ? "var(--color-accent)" : "var(--color-border)"}`,
                  background: routingMode === "explicit" ? "var(--color-accent-dim)" : "var(--color-bg-elevated)",
                  color: routingMode === "explicit" ? "var(--color-accent-hover)" : "var(--color-text-secondary)",
                  fontWeight: routingMode === "explicit" ? "var(--weight-semibold)" : "var(--weight-normal)",
                  fontSize: "var(--text-sm)",
                  cursor: "pointer",
                }}
              >
                EXPLICIT
              </button>
            </div>
            {routingMode === "auto" ? (
              <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", lineHeight: 1.5 }}>
                Il proxy userà il modello di default per ogni provider assegnato
              </p>
            ) : (
              <div>
                <label htmlFor="vk-model-select" style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", fontWeight: "var(--weight-medium)", display: "block", marginBottom: "var(--space-1)" }}>
                  Model
                </label>
                <select
                  id="vk-model-select"
                  value={modelPref}
                  onChange={(e) => setModelPref(e.target.value)}
                  style={{
                    width: "100%",
                    background: "var(--color-bg-elevated)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-md)",
                    padding: "var(--space-2) var(--space-3)",
                    color: "var(--color-text-primary)",
                    fontSize: "var(--text-sm)",
                  }}
                >
                  <option value="">— Select a model —</option>
                  {Array.from(new Set(selectableModels.map((m) => m.provider_slug))).map((slug) => (
                    <optgroup key={slug} label={slug}>
                      {selectableModels
                        .filter((m) => m.provider_slug === slug)
                        .map((m) => (
                          <option key={m.id} value={m.model_id}>
                            {m.display_name || m.model_id} [{m.tier}]
                            {m.supports_vision ? " 👁" : ""}
                            {m.supports_tools ? " 🛠" : ""}
                          </option>
                        ))}
                    </optgroup>
                  ))}
                </select>
                <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", lineHeight: 1.5, marginTop: "var(--space-1)" }}>
                  {assignedSlugs.size > 0
                    ? "Solo i modelli dei provider delle chiavi selezionate"
                    : "Seleziona prima le chiavi per filtrare i modelli per provider"}
                </p>
              </div>
            )}
          </div>

          <div>
            <label style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", fontWeight: "var(--weight-medium)", display: "block", marginBottom: "var(--space-2)" }}>
              Conversation memory
            </label>
            <div style={{ display: "flex", gap: "var(--space-2)", marginBottom: "var(--space-2)" }}>
              {(["off", "optional", "always"] as MemoryMode[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setMemoryMode(mode)}
                  style={{
                    padding: "var(--space-2) var(--space-4)",
                    borderRadius: "var(--radius-md)",
                    border: `1px solid ${memoryMode === mode ? "var(--color-accent)" : "var(--color-border)"}`,
                    background: memoryMode === mode ? "var(--color-accent-dim)" : "var(--color-bg-elevated)",
                    color: memoryMode === mode ? "var(--color-accent-hover)" : "var(--color-text-secondary)",
                    fontWeight: memoryMode === mode ? "var(--weight-semibold)" : "var(--weight-normal)",
                    fontSize: "var(--text-sm)",
                    cursor: "pointer",
                    textTransform: "uppercase",
                  }}
                >
                  {mode}
                </button>
              ))}
            </div>
            <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", lineHeight: 1.5 }}>
              {memoryMode === "off"
                ? "Nessuna memoria: ogni richiesta è indipendente (default)."
                : memoryMode === "optional"
                  ? "Memoria attiva solo se il client invia l'header X-Conversation-Id."
                  : "Memoria sempre attiva: il proxy genera/mantiene il thread automaticamente."}
            </p>
          </div>

          <div>
            <label style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", fontWeight: "var(--weight-medium)", display: "block", marginBottom: "var(--space-2)" }}>
              Assign API keys (select &amp; set priority)
            </label>
            {keys.length === 0 && (
              <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>No API keys available. Add keys first.</p>
            )}
            {keys.map((k) => {
              const assignment = assignments.find((a) => a.api_key_id === k.id);
              const selected = !!assignment;
              return (
                <div key={k.id} style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", padding: "var(--space-2) 0", borderBottom: "1px solid var(--color-border)" }}>
                  <input type="checkbox" checked={selected} onChange={() => toggleKey(k)} style={{ accentColor: "var(--color-accent)" }} />
                  <span style={{ flex: 1, fontSize: "var(--text-sm)" }}>
                    {k.name}{" "}
                    <span style={{ color: "var(--color-text-muted)", fontSize: "var(--text-xs)" }}>({k.provider_slug})</span>
                  </span>
                  {selected && (
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
                      <label style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>Priority:</label>
                      <input
                        type="number"
                        min={1}
                        max={99}
                        value={assignment.priority}
                        onChange={(e) => setAssignments((prev) => prev.map((a) => a.api_key_id === k.id ? { ...a, priority: Number(e.target.value) } : a))}
                        style={{ width: "60px", background: "var(--color-bg-elevated)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-sm)", padding: "var(--space-1) var(--space-2)", color: "var(--color-text-primary)", fontSize: "var(--text-xs)" }}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "flex-end", marginTop: "var(--space-2)" }}>
            {formError && (
              <p style={{ flex: 1, fontSize: "var(--text-xs)", color: "var(--color-error)", alignSelf: "center" }}>{formError}</p>
            )}
            <Button variant="secondary" type="button" onClick={() => { setOpen(false); resetForm(); setFormError(null); }}>Cancel</Button>
            <Button type="submit" loading={createMut.isPending}>Create</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
