import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { sendChatCompletion, API_FORMATS } from "../api/chat";
import type { ChatMessage, ApiFormat } from "../api/chat";
import { listModels } from "../api/models";
import { listVirtualKeys } from "../api/virtualKeys";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";

const VK_STORAGE_KEY = "apex-chat-virtual-key";
const SYSTEM_STORAGE_KEY = "apex-chat-system-prompt";
const FORMAT_STORAGE_KEY = "apex-chat-format";
const SAVED_KEYS_MAP = "apex-chat-keys";

function getSavedKeysMap(): Record<string, string> {
  try { return JSON.parse(localStorage.getItem(SAVED_KEYS_MAP) ?? "{}"); }
  catch { return {}; }
}

interface ChatTurn extends ChatMessage {
  id: string;
  error?: boolean;
}

function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  return "Errore inatteso";
}

function newId(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export default function Chat() {
  const { data: models = [] } = useQuery({
    queryKey: ["models", "active", "enabled"],
    queryFn: () => listModels({ active: true, enabled: true }),
  });
  const { data: vkeys = [] } = useQuery({ queryKey: ["vkeys"], queryFn: listVirtualKeys });

  const [virtualKey, setVirtualKey] = useState<string>(
    () => localStorage.getItem(VK_STORAGE_KEY) ?? "",
  );
  const savedMap = getSavedKeysMap();
  // Which vkey id matches the current plaintext (if saved via "Usa in Chat")
  const activeVkId = Object.entries(savedMap).find(([, v]) => v === virtualKey)?.[0] ?? null;
  const activeVkInfo = vkeys.find((k) => k.id === activeVkId) ?? null;
  const [systemPrompt, setSystemPrompt] = useState<string>(
    () => localStorage.getItem(SYSTEM_STORAGE_KEY) ?? "",
  );
  const [model, setModel] = useState<string>("auto");
  const [format, setFormat] = useState<ApiFormat>(
    () => (localStorage.getItem(FORMAT_STORAGE_KEY) as ApiFormat | null) ?? "openai",
  );
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    localStorage.setItem(VK_STORAGE_KEY, virtualKey);
  }, [virtualKey]);
  useEffect(() => {
    localStorage.setItem(SYSTEM_STORAGE_KEY, systemPrompt);
  }, [systemPrompt]);
  useEffect(() => {
    localStorage.setItem(FORMAT_STORAGE_KEY, format);
  }, [format]);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, busy]);

  const send = async () => {
    const text = draft.trim();
    if (!text || busy) return;
    if (!virtualKey.trim()) {
      setError("Inserisci una virtual key (apg-…) per usare il proxy.");
      return;
    }
    setError(null);

    const userTurn: ChatTurn = { id: newId(), role: "user", content: text };
    const nextTurns = [...turns, userTurn];
    setTurns(nextTurns);
    setDraft("");
    setBusy(true);

    // Client-side history: send the full thread each call (works with memory_mode=off).
    const messages: ChatMessage[] = [];
    if (systemPrompt.trim()) messages.push({ role: "system", content: systemPrompt.trim() });
    for (const t of nextTurns) messages.push({ role: t.role, content: t.content });

    try {
      const result = await sendChatCompletion({
        virtualKey: virtualKey.trim(),
        model,
        messages,
        format,
      });
      setTurns((prev) => [
        ...prev,
        { id: newId(), role: "assistant", content: result.content || "(risposta vuota)" },
      ]);
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      setTurns((prev) => [
        ...prev,
        { id: newId(), role: "assistant", content: `⚠ ${msg}`, error: true },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const modelGroups = Array.from(new Set(models.map((m) => m.provider_slug)));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)", height: "calc(100dvh - var(--space-12))" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "var(--space-3)" }}>
        <div>
          <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: "var(--weight-bold)", letterSpacing: "-0.02em" }}>Chat</h1>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginTop: "var(--space-1)" }}>
            Parla con i modelli attraverso il tuo proxy, usando una virtual key
          </p>
        </div>
        <div style={{ display: "flex", gap: "var(--space-2)", flexShrink: 0 }}>
          <Button variant="ghost" size="sm" onClick={() => setTurns([])} disabled={turns.length === 0}>
            New chat
          </Button>
        </div>
      </div>

      {/* Controls */}
      <Card>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
            <label htmlFor="chat-vk" style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", fontWeight: "var(--weight-medium)" }}>
              Virtual key
            </label>
            {vkeys.length > 0 && (
              <select
                aria-label="Seleziona virtual key salvata"
                value={activeVkId ?? ""}
                onChange={(e) => {
                  const id = e.target.value;
                  if (!id) { setVirtualKey(""); return; }
                  const saved = getSavedKeysMap()[id];
                  if (saved) { setVirtualKey(saved); }
                  else {
                    setVirtualKey("");
                    setError(`La key "${vkeys.find(k => k.id === id)?.name}" non è salvata nel browser. Vai su Virtual Keys → Ruota → Usa in Chat.`);
                  }
                }}
                style={{
                  background: "var(--color-bg-elevated)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  padding: "var(--space-2) var(--space-3)",
                  color: "var(--color-text-primary)",
                  fontSize: "var(--text-sm)",
                }}
              >
                <option value="">— seleziona key —</option>
                {vkeys.map((vk) => {
                  const hasSaved = !!getSavedKeysMap()[vk.id];
                  return (
                    <option key={vk.id} value={vk.id}>
                      {vk.name} ({vk.key_prefix}…){hasSaved ? " ✓" : " — non salvata"}
                    </option>
                  );
                })}
              </select>
            )}
            <input
              id="chat-vk"
              type="password"
              value={virtualKey}
              onChange={(e) => setVirtualKey(e.target.value)}
              placeholder="apg-… (oppure seleziona sopra)"
              autoComplete="off"
              style={{
                background: "var(--color-bg-elevated)",
                border: `1px solid ${activeVkInfo ? "var(--color-success)" : "var(--color-border)"}`,
                borderRadius: "var(--radius-md)",
                padding: "var(--space-2) var(--space-3)",
                color: "var(--color-text-primary)",
                fontSize: "var(--text-sm)",
                fontFamily: "var(--font-mono)",
              }}
            />
            {activeVkInfo ? (
              <span style={{ fontSize: "var(--text-xs)", color: "var(--color-success)" }}>
                ✓ {activeVkInfo.name} · {activeVkInfo.key_prefix}… · memory: {activeVkInfo.memory_mode}
              </span>
            ) : (
              <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
                {vkeys.length > 0
                  ? "Seleziona dal menu ↑ (✓ = disponibile) oppure incolla il plaintext apg-…"
                  : "Crea una virtual key, poi usa il bottone \"Usa in Chat\"."}
              </span>
            )}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
            <label htmlFor="chat-model" style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", fontWeight: "var(--weight-medium)" }}>
              Modello
            </label>
            <select
              id="chat-model"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              style={{
                background: "var(--color-bg-elevated)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                padding: "var(--space-2) var(--space-3)",
                color: "var(--color-text-primary)",
                fontSize: "var(--text-sm)",
              }}
            >
              <option value="auto">auto (routing / preferenza della key)</option>
              {modelGroups.map((slug) => (
                <optgroup key={slug} label={slug}>
                  {models
                    .filter((m) => m.provider_slug === slug)
                    .map((m) => (
                      <option key={m.id} value={m.model_id}>
                        {m.display_name || m.model_id} [{m.tier}]
                      </option>
                    ))}
                </optgroup>
              ))}
            </select>
            <input
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="System prompt (opzionale)"
              style={{
                marginTop: "var(--space-1)",
                background: "var(--color-bg-elevated)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                padding: "var(--space-2) var(--space-3)",
                color: "var(--color-text-primary)",
                fontSize: "var(--text-sm)",
              }}
            />
            <label htmlFor="chat-format" style={{ marginTop: "var(--space-2)", fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", fontWeight: "var(--weight-medium)" }}>
              Formato API
            </label>
            <select
              id="chat-format"
              value={format}
              onChange={(e) => setFormat(e.target.value as ApiFormat)}
              style={{
                background: "var(--color-bg-elevated)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                padding: "var(--space-2) var(--space-3)",
                color: "var(--color-text-primary)",
                fontSize: "var(--text-sm)",
              }}
            >
              {API_FORMATS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
            <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
              Endpoint &amp; shape di output: OpenAI, Anthropic, Gemini o Ollama
            </span>
          </div>
        </div>
      </Card>

      {/* Thread */}
      <Card style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", padding: 0, overflow: "hidden" }}>
        <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", padding: "var(--space-5)", display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          {turns.length === 0 && (
            <div style={{ margin: "auto", textAlign: "center", color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
              Scrivi un messaggio per iniziare la conversazione.
            </div>
          )}
          {turns.map((t) => (
            <div
              key={t.id}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "var(--space-1)",
                alignItems: t.role === "user" ? "flex-end" : "flex-start",
              }}
            >
              <Badge variant={t.role === "user" ? "info" : t.error ? "error" : "neutral"}>
                {t.role}
              </Badge>
              <div
                style={{
                  maxWidth: "80%",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  background: t.role === "user" ? "var(--color-accent-dim)" : "var(--color-bg-elevated)",
                  border: `1px solid ${t.error ? "var(--color-error)" : "var(--color-border)"}`,
                  borderRadius: "var(--radius-lg)",
                  padding: "var(--space-3) var(--space-4)",
                  color: t.error ? "var(--color-error)" : "var(--color-text-primary)",
                  fontSize: "var(--text-sm)",
                  lineHeight: 1.6,
                }}
              >
                {t.content}
              </div>
            </div>
          ))}
          {busy && (
            <div style={{ alignSelf: "flex-start", color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
              …sto pensando
            </div>
          )}
        </div>

        {/* Composer */}
        <div style={{ borderTop: "1px solid var(--color-border)", padding: "var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          {error && (
            <p style={{ fontSize: "var(--text-xs)", color: "var(--color-error)", margin: 0 }}>{error}</p>
          )}
          <div style={{ display: "flex", gap: "var(--space-3)", alignItems: "flex-end" }}>
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Messaggio…  (Invio per inviare, Shift+Invio per a capo)"
              rows={2}
              style={{
                flex: 1,
                resize: "none",
                background: "var(--color-bg-elevated)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                padding: "var(--space-3)",
                color: "var(--color-text-primary)",
                fontSize: "var(--text-sm)",
                fontFamily: "inherit",
                lineHeight: 1.5,
                outline: "none",
              }}
            />
            <Button onClick={send} loading={busy} disabled={!draft.trim()}>
              Invia
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
