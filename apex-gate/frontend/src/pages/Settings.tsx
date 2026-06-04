import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { getMe } from '../api/auth';
import type { UserResponse } from '../api/auth';
import client from '../api/client';
import { useAuthStore } from '../store/authStore';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import styles from './Settings.module.css';

interface ProfilePatch {
  username?: string;
  email?: string;
  current_password?: string;
  new_password?: string;
}

async function patchProfile(body: ProfilePatch): Promise<UserResponse> {
  const { data } = await client.patch<UserResponse>('/auth/me', body);
  return data;
}

function getErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const res = (err as { response?: { data?: { detail?: string } } }).response;
    if (res?.data?.detail) return String(res.data.detail);
  }
  if (err instanceof Error) return err.message;
  return 'An unexpected error occurred';
}

export default function Settings() {
  const navigate = useNavigate();
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const setUser = useAuthStore((s) => s.setUser);

  const { data: me } = useQuery<UserResponse>({ queryKey: ['me'], queryFn: getMe });

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [profileMsg, setProfileMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const profileMutation = useMutation({
    mutationFn: patchProfile,
    onSuccess: (updated) => {
      setUser(updated);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setProfileMsg({ type: 'success', text: 'Profile updated successfully' });
      setTimeout(() => setProfileMsg(null), 4000);
    },
    onError: (err: unknown) => {
      setProfileMsg({ type: 'error', text: getErrorMessage(err) });
    },
  });

  function handleProfileSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (newPassword && newPassword !== confirmPassword) {
      setProfileMsg({ type: 'error', text: 'New passwords do not match' });
      return;
    }
    const patch: ProfilePatch = {};
    if (username.trim()) patch.username = username.trim();
    if (email.trim()) patch.email = email.trim();
    if (currentPassword) patch.current_password = currentPassword;
    if (newPassword) patch.new_password = newPassword;
    if (Object.keys(patch).length === 0) return;
    profileMutation.mutate(patch);
  }

  function handleLogout() {
    clearAuth();
    void navigate('/login');
  }

  return (
    <div className={styles.page}>
      <div className={styles.heading}>
        <h1 className={styles.title}>Settings</h1>
        <p className={styles.subtitle}>Manage your account and gateway preferences</p>
      </div>

      {/* Profile section */}
      <Card>
        <h2 className={styles.sectionTitle}>Profile</h2>
        <p className={styles.sectionDesc}>
          Currently signed in as <strong className={styles.highlight}>{me?.username ?? '...'}</strong>
          {me?.email ? <> ({me.email})</> : null}
        </p>
        <form className={styles.form} onSubmit={handleProfileSubmit}>
          <div className={styles.formRow}>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="username">New username</label>
              <input
                id="username"
                className={styles.input}
                type="text"
                placeholder={me?.username ?? 'Username'}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="email">New email</label>
              <input
                id="email"
                className={styles.input}
                type="email"
                placeholder={me?.email ?? 'Email address'}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </div>
          </div>
          <div className={styles.divider} />
          <p className={styles.fieldGroup}>Change password</p>
          <div className={styles.formRow}>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="current-pw">Current password</label>
              <input
                id="current-pw"
                className={styles.input}
                type="password"
                placeholder="Current password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="new-pw">New password</label>
              <input
                id="new-pw"
                className={styles.input}
                type="password"
                placeholder="New password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="confirm-pw">Confirm new password</label>
              <input
                id="confirm-pw"
                className={styles.input}
                type="password"
                placeholder="Confirm new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
              />
            </div>
          </div>
          {profileMsg && (
            <p className={profileMsg.type === 'success' ? styles.msgSuccess : styles.msgError}>
              {profileMsg.text}
            </p>
          )}
          <div className={styles.formActions}>
            <Button type="submit" variant="primary" loading={profileMutation.isPending}>
              Save changes
            </Button>
          </div>
        </form>
      </Card>

      {/* Discovery section */}
      <Card>
        <h2 className={styles.sectionTitle}>Discovery</h2>
        <p className={styles.sectionDesc}>
          Configure how frequently APEX GATE scans for new models.
        </p>
        <div className={styles.field} style={{ maxWidth: 260 }}>
          <label className={styles.label} htmlFor="discovery-interval">Discovery interval</label>
          <select id="discovery-interval" className={styles.select} defaultValue="6h">
            <option value="1h">Every 1 hour</option>
            <option value="3h">Every 3 hours</option>
            <option value="6h">Every 6 hours</option>
            <option value="12h">Every 12 hours</option>
            <option value="24h">Every 24 hours</option>
          </select>
        </div>
        <p className={styles.note}>
          Changes require a gateway restart to take effect.
        </p>
      </Card>

      {/* Danger zone */}
      <Card className={styles.dangerCard}>
        <h2 className={styles.dangerTitle}>Danger zone</h2>
        <p className={styles.sectionDesc}>
          Irreversible actions. Proceed with caution.
        </p>
        <div className={styles.dangerRow}>
          <div>
            <p className={styles.dangerActionTitle}>Sign out</p>
            <p className={styles.dangerActionDesc}>Ends your current session and clears stored credentials.</p>
          </div>
          <Button variant="danger" onClick={handleLogout}>
            Log out
          </Button>
        </div>
      </Card>
    </div>
  );
}
