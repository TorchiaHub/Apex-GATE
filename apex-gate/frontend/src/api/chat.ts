import client from "./client";

/** Base URL of the APEX GATE proxy (OpenAI-compatible surface). */
export const PROXY_BASE_URL: string =
  (import.meta.env.VITE_PROXY_BASE_URL as string | undefined) ?? "http://localhost:8000";

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface ChatCompletionResult {
  content: string;
  model: string | null;
  conversationId: string | null;
}

/** API formats supported by the proxy, each with its own endpoint + I/O shape. */
export type ApiFormat = "openai" | "anthropic" | "gemini" | "ollama";

export const API_FORMATS: { value: ApiFormat; label: string }[] = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "gemini", label: "Gemini" },
  { value: "ollama", label: "Ollama" },
];

interface FormatSpec {
  path: string;
  /** Build the request body from model + messages (OpenAI-style roles). */
  buildBody: (model: string, messages: ChatMessage[]) => unknown;
  /** Extract the assistant text + model from the protocol-specific response. */
  parse: (data: unknown) => { content: string; model: string | null };
}

const DEFAULT_MAX_TOKENS = 2048;

const FORMAT_SPECS: Record<ApiFormat, FormatSpec> = {
  openai: {
    path: "/v1/chat/completions",
    buildBody: (model, messages) => ({ model, messages, stream: false }),
    parse: (data) => {
      const d = data as { model?: string; choices?: { message?: { content?: string } }[] };
      return { content: d.choices?.[0]?.message?.content ?? "", model: d.model ?? null };
    },
  },
  anthropic: {
    path: "/anthropic/v1/messages",
    buildBody: (model, messages) => {
      const system = messages
        .filter((m) => m.role === "system")
        .map((m) => m.content)
        .join("\n\n");
      const convo = messages
        .filter((m) => m.role !== "system")
        .map((m) => ({ role: m.role, content: m.content }));
      return {
        model,
        ...(system ? { system } : {}),
        messages: convo,
        max_tokens: DEFAULT_MAX_TOKENS,
        stream: false,
      };
    },
    parse: (data) => {
      const d = data as { model?: string; content?: { text?: string }[] };
      return { content: d.content?.[0]?.text ?? "", model: d.model ?? null };
    },
  },
  gemini: {
    path: "/gemini/v1/generateContent",
    buildBody: (model, messages) => {
      const systemText = messages
        .filter((m) => m.role === "system")
        .map((m) => m.content)
        .join("\n\n");
      const contents = messages
        .filter((m) => m.role !== "system")
        .map((m) => ({
          role: m.role === "assistant" ? "model" : "user",
          parts: [{ text: m.content }],
        }));
      return {
        model,
        ...(systemText ? { systemInstruction: { parts: [{ text: systemText }] } } : {}),
        contents,
      };
    },
    parse: (data) => {
      const d = data as {
        modelVersion?: string;
        candidates?: { content?: { parts?: { text?: string }[] } }[];
      };
      const text = (d.candidates?.[0]?.content?.parts ?? [])
        .map((p) => p.text ?? "")
        .join("");
      return { content: text, model: d.modelVersion ?? null };
    },
  },
  ollama: {
    path: "/ollama/api/chat",
    buildBody: (model, messages) => ({ model, messages, stream: false }),
    parse: (data) => {
      const d = data as { model?: string; message?: { content?: string } };
      return { content: d.message?.content ?? "", model: d.model ?? null };
    },
  },
};

/**
 * Send a chat completion to the proxy using a *virtual key* (apg-…) as Bearer.
 * This deliberately bypasses the JWT axios client: the proxy authenticates
 * with the virtual key, not the dashboard session token.
 *
 * The `format` selects the endpoint and request/response shape (OpenAI,
 * Anthropic, Gemini, or Ollama compatible surface).
 */
export async function sendChatCompletion(params: {
  virtualKey: string;
  model: string;
  messages: ChatMessage[];
  format?: ApiFormat;
  conversationId?: string | null;
  signal?: AbortSignal;
}): Promise<ChatCompletionResult> {
  const spec = FORMAT_SPECS[params.format ?? "openai"];

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${params.virtualKey}`,
  };
  if (params.conversationId) headers["X-Conversation-Id"] = params.conversationId;

  const res = await fetch(`${PROXY_BASE_URL}${spec.path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(spec.buildBody(params.model, params.messages)),
    signal: params.signal,
  });

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      detail = typeof body?.detail === "string" ? body.detail : JSON.stringify(body?.detail ?? body);
    } catch {
      /* keep status text */
    }
    throw new Error(detail);
  }

  const data: unknown = await res.json();
  const parsed = spec.parse(data);
  return {
    content: parsed.content,
    model: parsed.model,
    conversationId: res.headers.get("X-Conversation-Id"),
  };
}

// ── Server-side conversation management (JWT-scoped, current user) ──────────

export interface Conversation {
  id: string;
  virtual_key_id: string;
  title: string | null;
  message_count: number;
  total_tokens: number;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  expires_at: string | null;
}

export interface ConversationMessage {
  id: string;
  role: string;
  content: string;
  token_count: number;
  created_at: string;
}

export const listConversations = async (
  virtualKeyId?: string,
): Promise<Conversation[]> => {
  const { data } = await client.get<Conversation[]>("/api/v1/conversations/", {
    params: virtualKeyId ? { virtual_key_id: virtualKeyId } : undefined,
  });
  return data;
};

export const listConversationMessages = async (
  conversationId: string,
): Promise<ConversationMessage[]> => {
  const { data } = await client.get<ConversationMessage[]>(
    `/api/v1/conversations/${conversationId}/messages`,
  );
  return data;
};

export const deleteConversation = async (conversationId: string): Promise<void> => {
  await client.delete(`/api/v1/conversations/${conversationId}`);
};
