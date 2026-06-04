import client from "./client";

export interface ApiKey {
  id: string;
  provider_id: string;
  provider_slug: string;
  name: string;
  key_masked: string;
  tier: string;
  priority: number;
  is_enabled: boolean;
  created_at: string;
  rate_limit_rpm?: number | null;
  rate_limit_rpd?: number | null;
  budget_daily_usd?: number | null;
  budget_monthly_usd?: number | null;
  status?: string | null;
  provider_name?: string | null;
}

export interface ApiKeyCreate {
  provider_id: string;
  name: string;
  api_key_plaintext: string;
  tier?: string;
  rate_limit_rpm?: number | null;
  rate_limit_rpd?: number | null;
}

export const listKeys = async (): Promise<ApiKey[]> => {
  const { data } = await client.get<ApiKey[]>("/api/v1/keys/");
  return data;
};

export const createKey = async (body: ApiKeyCreate): Promise<ApiKey> => {
  const { data } = await client.post<ApiKey>("/api/v1/keys/", body);
  return data;
};

export const updateKey = async (id: string, body: Partial<Pick<ApiKey, "name" | "priority" | "is_enabled" | "tier">>): Promise<ApiKey> => {
  const { data } = await client.patch<ApiKey>(`/api/v1/keys/${id}`, body);
  return data;
};

export const deleteKey = async (id: string): Promise<void> => {
  await client.delete(`/api/v1/keys/${id}`);
};

export const testKey = async (id: string): Promise<{ ok: boolean; latency_ms: number; error?: string }> => {
  const { data } = await client.post(`/api/v1/keys/${id}/test`);
  return data;
};
