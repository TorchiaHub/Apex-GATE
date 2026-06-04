import client from "./client";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  username: string;
  email: string;
  is_admin: boolean;
  is_active: boolean;
}

export const login = async (username: string, password: string): Promise<TokenResponse> => {
  const { data } = await client.post<TokenResponse>("/auth/login", { username, password });
  return data;
};

export const register = async (username: string, email: string, password: string): Promise<UserResponse> => {
  const { data } = await client.post<UserResponse>("/auth/register", { username, email, password });
  return data;
};

export const getMe = async (): Promise<UserResponse> => {
  const { data } = await client.get<UserResponse>("/auth/me");
  return data;
};

export const logout = async (refreshToken: string): Promise<void> => {
  await client.post("/auth/logout", { refresh_token: refreshToken });
};
