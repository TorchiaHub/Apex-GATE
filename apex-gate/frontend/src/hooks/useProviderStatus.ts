import { useEffect, useRef, useState } from "react";
import { useAuthStore } from "../store/authStore";

interface ProviderStatus {
  provider: string;
  slug: string;
  total_keys: number;
  active_keys: number;
  exhausted_keys: number;
  disabled_keys: number;
}

interface StatusPayload {
  ts: string;
  providers: ProviderStatus[];
}

export function useProviderStatus(): StatusPayload | null {
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const accessToken = useAuthStore((s) => s.accessToken);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!accessToken) {
      setStatus(null);
      return;
    }

    let closedByCleanup = false;
    let attempts = 0;
    let ws: WebSocket | null = null;

    const connect = () => {
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(
        `${proto}://${window.location.host}/ws/status?token=${encodeURIComponent(accessToken)}`
      );

      ws.onopen = () => {
        attempts = 0;
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          setStatus(JSON.parse(event.data as string) as StatusPayload);
        } catch {
          // ignore malformed frames
        }
      };

      ws.onclose = () => {
        if (closedByCleanup) return;
        // Exponential backoff capped at 30s, then retry.
        const delay = Math.min(1000 * 2 ** attempts, 30000);
        attempts += 1;
        reconnectTimer.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        ws?.close();
      };
    };

    connect();

    return () => {
      closedByCleanup = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      ws?.close();
    };
  }, [accessToken]);

  return status;
}
