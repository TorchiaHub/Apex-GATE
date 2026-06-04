import client from "./client";

export interface OverviewStats {
  calls_today: number;
  tokens_today: number;
  cost_today: string;
}

export interface ProviderStat {
  provider: string;
  calls: number;
  cost: string;
}

export interface ModelStat {
  model_id: string;
  calls: number;
  avg_latency_ms: number | null;
}

export interface DayStat {
  date: string;
  calls: number;
  cost: string;
}

export interface CostStat {
  key_name: string;
  total_cost: string;
}

export const fetchOverview = async (): Promise<OverviewStats> => {
  const { data } = await client.get<OverviewStats>("/api/v1/stats/overview");
  return data;
};

export const fetchByProvider = async (): Promise<ProviderStat[]> => {
  const { data } = await client.get<ProviderStat[]>("/api/v1/stats/by-provider");
  return data;
};

export const fetchByModel = async (): Promise<ModelStat[]> => {
  const { data } = await client.get<ModelStat[]>("/api/v1/stats/by-model");
  return data;
};

export const fetchByDay = async (): Promise<DayStat[]> => {
  const { data } = await client.get<DayStat[]>("/api/v1/stats/by-day");
  return data;
};

export const fetchCosts = async (): Promise<CostStat[]> => {
  const { data } = await client.get<CostStat[]>("/api/v1/stats/costs");
  return data;
};
