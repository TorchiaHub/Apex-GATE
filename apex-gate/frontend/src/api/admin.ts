import client from "./client";

export interface AdminUser {
  id: string;
  username: string;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export const listUsers = async (): Promise<AdminUser[]> => {
  const { data } = await client.get<AdminUser[]>("/api/v1/admin/users");
  return data;
};

export const updateUser = async (id: string, body: Partial<Pick<AdminUser, "is_admin" | "is_active" | "email">>): Promise<AdminUser> => {
  const { data } = await client.patch<AdminUser>(`/api/v1/admin/users/${id}`, body);
  return data;
};

export const deleteUser = async (id: string): Promise<void> => {
  await client.delete(`/api/v1/admin/users/${id}`);
};

export const resetExhaustions = async (): Promise<void> => {
  await client.post("/api/v1/admin/reset-exhaustions");
};
