/**
 * useApplicationSocket — WebSocket hook for real-time application status updates.
 *
 * Connects to ws://<API>/ws/applications, authenticates with JWT,
 * and dispatches incoming events to the provided callback.
 *
 * Features:
 * - Reconnection with exponential backoff (1s → 2s → 4s … 30s cap)
 * - Client-side ping every 30s to detect stale connections
 * - Falls back to HTTP polling if WebSocket fails after MAX_RETRIES
 * - Automatically cleans up on unmount or token change
 */

import { useEffect, useRef, useCallback } from 'react';
import { getToken } from '@/lib/api';

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000')
  .replace(/^http/, 'ws');

const MAX_RETRIES = 5;
const BASE_DELAY_MS = 1_000;
const MAX_DELAY_MS = 30_000;
const PING_INTERVAL_MS = 30_000;
const POLL_INTERVAL_MS = 15_000;

type EventHandler = (event: { type: string; payload: Record<string, unknown> }) => void;

interface UseSocketOpts {
  /** Called whenever a real-time event arrives (WS or poll). */
  onEvent: EventHandler;
  /** HTTP polling fallback — called periodically when WS is unavailable. */
  onPollFallback: () => Promise<void>;
  /** Whether the user is authenticated (controls connect/disconnect). */
  enabled: boolean;
}

export function useApplicationSocket({ onEvent, onPollFallback, enabled }: UseSocketOpts) {
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const unmountedRef = useRef(false);

  const clearTimers = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (pingTimerRef.current) {
      clearInterval(pingTimerRef.current);
      pingTimerRef.current = null;
    }
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    if (pollTimerRef.current) return; // already polling
    pollTimerRef.current = setInterval(() => {
      onPollFallback().catch(() => {});
    }, POLL_INTERVAL_MS);
  }, [onPollFallback]);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (unmountedRef.current) return;
    const token = getToken();
    if (!token) return;

    // Close any existing connection
    if (wsRef.current) {
      try { wsRef.current.close(); } catch { /* ignore */ }
    }

    const ws = new WebSocket(`${WS_BASE}/ws/applications`);
    wsRef.current = ws;

    ws.onopen = () => {
      // Send auth token immediately after connection opens
      ws.send(JSON.stringify({ token }));
      retriesRef.current = 0;
      stopPolling();

      // Start keep-alive pings
      pingTimerRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, PING_INTERVAL_MS);
    };

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        // Ignore pong responses
        if (data.type === 'pong') return;
        onEvent(data);
      } catch {
        /* malformed message — ignore */
      }
    };

    ws.onclose = () => {
      if (pingTimerRef.current) {
        clearInterval(pingTimerRef.current);
        pingTimerRef.current = null;
      }

      if (unmountedRef.current) return;

      retriesRef.current += 1;
      if (retriesRef.current > MAX_RETRIES) {
        // Exceeded retry limit — fall back to HTTP polling
        startPolling();
        return;
      }

      // Exponential backoff: 1s, 2s, 4s, 8s, 16s, capped at 30s
      const delay = Math.min(BASE_DELAY_MS * 2 ** (retriesRef.current - 1), MAX_DELAY_MS);
      reconnectTimerRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      // onclose will fire after onerror — reconnection handled there
    };
  }, [onEvent, startPolling, stopPolling]);

  useEffect(() => {
    unmountedRef.current = false;

    if (enabled) {
      connect();
    }

    return () => {
      unmountedRef.current = true;
      clearTimers();
      if (wsRef.current) {
        try { wsRef.current.close(); } catch { /* ignore */ }
        wsRef.current = null;
      }
    };
  }, [enabled, connect, clearTimers]);
}
