import client from "./client";

export interface Provider {
  id: string;
  slug: string;
  name: string;
  protocol: string;
  litellm_prefix: string;
  supports_free_tier: boolean;
  key_count: number;
  sort_order: number;
  logo_url: string | null;
}

export interface ProviderModel {
  id: string;
  model_id: string;
  display_name: string;
  tier: string;
  context_window: number;
  is_active: boolean;
  is_default?: boolean;
}

export const listProviders = async (): Promise<Provider[]> => {
  const { data } = await client.get<Provider[]>("/api/v1/providers/");
  return data;
};

export const getProviderModels = async (slug: string): Promise<ProviderModel[]> => {
  const { data } = await client.get<ProviderModel[]>(`/api/v1/providers/${slug}/models`);
  return data;
};

export interface ProviderCreate {
  name: string;
  api_base_url: string;
  protocol?: string;
  supports_free_tier?: boolean;
}

export const createProvider = async (data: ProviderCreate): Promise<Provider> => {
  const { data: res } = await client.post<Provider>("/api/v1/providers/", data);
  return res;
};
