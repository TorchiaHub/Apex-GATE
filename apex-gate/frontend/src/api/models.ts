import client from "./client";

export interface ModelCatalogItem {
  id: string;
  provider_id: string;
  provider_slug: string;
  model_id: string;
  display_name: string;
  context_window: number | null;
  tier: "free" | "paid";
  cost_input_per_1m_usd: string | null;
  cost_output_per_1m_usd: string | null;
  supports_vision: boolean;
  supports_tools: boolean;
  supports_streaming: boolean;
  is_active: boolean;
  is_enabled: boolean;
  is_default: boolean;
  last_discovered_at: string;
}

export interface ModelListParams {
  provider?: string;
  tier?: string;
  active?: boolean;
  enabled?: boolean;
  is_default?: boolean;
}

export const listModels = async (params?: ModelListParams): Promise<ModelCatalogItem[]> => {
  const { data } = await client.get<ModelCatalogItem[]>('/api/v1/models/', { params });
  return data;
};

export const listDefaultModels = async (): Promise<ModelCatalogItem[]> => {
  const { data } = await client.get<ModelCatalogItem[]>('/api/v1/models/', { params: { is_default: true } });
  return data;
};

export const refreshModels = async (): Promise<{ message: string }> => {
  const { data } = await client.post<{ message: string }>('/api/v1/models/refresh');
  return data;
};

export const setModelEnabled = async (
  modelId: string,
  isEnabled: boolean,
): Promise<ModelCatalogItem> => {
  const { data } = await client.patch<ModelCatalogItem>(`/api/v1/models/${modelId}`, {
    is_enabled: isEnabled,
  });
  return data;
};