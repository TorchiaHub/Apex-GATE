import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listUsers, updateUser, deleteUser, resetExhaustions } from "../api/admin";
import { useAuthStore } from "../store/authStore";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";

export default function Admin() {
  const { user: me } = useAuthStore();
  const qc = useQueryClient();
  const { data: users = [] } = useQuery({ queryKey: ["admin.users"], queryFn: listUsers });

  const updateMut = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Parameters<typeof updateUser>[1] }) => updateUser(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin.users"] }),
  });

  const deleteMut = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin.users"] }),
  });

  const resetMut = useMutation({ mutationFn: resetExhaustions });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: "var(--weight-bold)", letterSpacing: "-0.02em" }}>Admin</h1>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginTop: "var(--space-1)" }}>User management and system actions</p>
        </div>
        <Button
          variant="secondary"
          onClick={() => { if (confirm("Reset all rate-limit states?")) resetMut.mutate(); }}
          loading={resetMut.isPending}
        >
          Reset exhaustions
        </Button>
      </div>

      <Card>
        <h2 style={{ fontSize: "var(--text-base)", fontWeight: "var(--weight-semibold)", marginBottom: "var(--space-4)" }}>Users</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          {users.map((u) => (
            <div key={u.id} style={{ display: "flex", alignItems: "center", gap: "var(--space-4)", flexWrap: "wrap", padding: "var(--space-3) 0", borderBottom: "1px solid var(--color-border-subtle)" }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: "var(--space-1)" }}>
                  <span style={{ fontWeight: "var(--weight-medium)", fontSize: "var(--text-sm)" }}>{u.username}</span>
                  {u.is_admin && <Badge variant="info">admin</Badge>}
                  <Badge variant={u.is_active ? "success" : "error"}>{u.is_active ? "active" : "inactive"}</Badge>
                </div>
                <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>{u.email}</span>
              </div>
              {u.id !== me?.id && (
                <div style={{ display: "flex", gap: "var(--space-2)", flexShrink: 0 }}>
                  <Button variant="ghost" size="sm" onClick={() => updateMut.mutate({ id: u.id, body: { is_active: !u.is_active } })}>
                    {u.is_active ? "Deactivate" : "Activate"}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => updateMut.mutate({ id: u.id, body: { is_admin: !u.is_admin } })}>
                    {u.is_admin ? "Remove admin" : "Make admin"}
                  </Button>
                  <Button variant="danger" size="sm" onClick={() => { if (confirm(`Delete user ${u.username}?`)) deleteMut.mutate(u.id); }}>
                    Delete
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
