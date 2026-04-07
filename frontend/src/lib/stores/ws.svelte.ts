import type { Job } from '$lib/api/scan';

export type WsStatus = 'connecting' | 'connected' | 'disconnected';

export interface ScannerUpdate {
  uri: string;
  online: boolean;
  name: string;
}

function createWsStore() {
  let status = $state<WsStatus>('disconnected');
  let lastJobUpdate = $state<Job | null>(null);
  let lastScannerUpdate = $state<ScannerUpdate | null>(null);

  let ws: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let pingTimer: ReturnType<typeof setInterval> | null = null;
  let enabled = false;

  function clearTimers() {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (pingTimer !== null) {
      clearInterval(pingTimer);
      pingTimer = null;
    }
  }

  function connect() {
    if (!enabled) return;
    if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) return;

    status = 'connecting';

    const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${location.host}/api/v1/ws${token ? `?token=${token}` : ''}`;

    try {
      ws = new WebSocket(url);
    } catch {
      status = 'disconnected';
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      status = 'connected';
      // Keep-alive pings
      pingTimer = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 25000);
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string) as {
          type: string;
          data?: unknown;
        };
        if (msg.type === 'job_update' && msg.data) {
          lastJobUpdate = msg.data as Job;
        } else if (msg.type === 'scanner_update' && msg.data) {
          lastScannerUpdate = msg.data as ScannerUpdate;
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onerror = () => {
      // error event is always followed by close
    };

    ws.onclose = () => {
      clearTimers();
      if (enabled) {
        status = 'disconnected';
        scheduleReconnect();
      }
    };
  }

  function scheduleReconnect() {
    if (!enabled) return;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, 3000);
  }

  function disconnect() {
    enabled = false;
    clearTimers();
    if (ws) {
      ws.onclose = null;
      ws.close();
      ws = null;
    }
    status = 'disconnected';
  }

  function start() {
    enabled = true;
    connect();
  }

  return {
    get status() {
      return status;
    },
    get lastJobUpdate() {
      return lastJobUpdate;
    },
    get lastScannerUpdate() {
      return lastScannerUpdate;
    },
    start,
    disconnect
  };
}

export const wsStore = createWsStore();
