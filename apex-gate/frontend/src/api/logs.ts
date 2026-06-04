import client from "./client";

export interface RequestLog {
  id: string;
  model_id: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: string;
  latency_ms: number | null;
  status: string;
  protocol: string | null;
  created_at: string;
  virtual_key_id: string | null;
  api_key_id: string | null;
}

export interface LogFilters {
  limit?: number;
  offset?: number;
  status?: string;
  virtual_key_id?: string;
  date_from?: string;
  date_to?: string;
}

export const fetchLogs = async (filters: LogFilters = {}): Promise<RequestLog[]> => {
  const { data } = await client.get<RequestLog[]>("/api/v1/logs/", { params: filters });
  return data;
};
