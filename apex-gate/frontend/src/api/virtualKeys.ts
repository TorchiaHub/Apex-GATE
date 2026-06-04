import client from "./client";

export interface KeyAssignment {
  api_key_id: string;
  priority: number;
}

export type MemoryMode = "off" | "optional" | "always";

export interface VirtualKey {
  id: string;
  name: string;
  key_prefix: string;
  daily_token_budget: number | null;
  is_enabled: boolean;
  model_preference: string | null;
  memory_mode: MemoryMode;
  memory_max_messages: number;
  memory_max_context_tokens: number;
  memory_ttl_hours: number;
  created_at: string;
  assignments?: { api_key_id: string; priority: number; key_name?: string }[];
}

export interface VirtualKeyWithPlaintext extends VirtualKey {
  key_plaintext: string;
}

export const listVirtualKeys = async (): Promise<VirtualKey[]> => {
  const { data } = await client.get<VirtualKey[]>("/api/v1/virtual-keys/");
  return data;
};

export const createVirtualKey = async (body: {
  name: string;
  daily_token_budget?: number;
  assignments?: KeyAssignment[];
  is_enabled?: boolean;
  model_preference?: string | null;
  memory_mode?: MemoryMode;
  memory_max_messages?: number;
  memory_max_context_tokens?: number;
  memory_ttl_hours?: number;
}): Promise<VirtualKeyWithPlaintext> => {
  const { data } = await client.post<VirtualKeyWithPlaintext>("/api/v1/virtual-keys/", body);
  return data;
};

export const rotateVirtualKey = async (id: string): Promise<VirtualKeyWithPlaintext> => {
  const { data } = await client.post<VirtualKeyWithPlaintext>(`/api/v1/virtual-keys/${id}/rotate`);
  return data;
};

export const updateVirtualKey = async (
  id: string,
  body: Partial<
    Pick<
      VirtualKey,
      | "name"
      | "daily_token_budget"
      | "is_enabled"
      | "model_preference"
      | "memory_mode"
      | "memory_max_messages"
      | "memory_max_context_tokens"
      | "memory_ttl_hours"
    > & { assignments?: KeyAssignment[] }
  >
): Promise<VirtualKey> => {
  const { data } = await client.patch<VirtualKey>(`/api/v1/virtual-keys/${id}`, body);
  return data;
};

export const deleteVirtualKey = async (id: string): Promise<void> => {
  await client.delete(`/api/v1/virtual-keys/${id}`);
};
