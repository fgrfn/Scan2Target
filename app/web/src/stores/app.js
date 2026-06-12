import { writable, get } from 'svelte/store';
import { api, setToken, getToken, setUnauthorizedHandler } from '../lib/api';
import { isActive } from '../lib/status';

export const pages = [
  { id: 'dashboard', icon: 'dashboard', group: 'scan' },
  { id: 'new-scan', icon: 'scan', group: 'scan' },
  { id: 'history', icon: 'history', group: 'scan' },
  { id: 'devices', icon: 'devices', group: 'manage' },
  { id: 'targets', icon: 'targets', group: 'manage' },
  { id: 'statistics', icon: 'stats', group: 'manage' },
  { id: 'settings', icon: 'settings', group: 'manage' }
];

const SETTINGS_KEY = 'scan2target_settings';

function loadSettings() {
  const defaults = { autoRefresh: true, compactTables: false };
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return defaults;
    const parsed = JSON.parse(raw);
    return { autoRefresh: parsed.autoRefresh !== false, compactTables: parsed.compactTables === true };
  } catch {
    return defaults;
  }
}

function persistSettings(settings) {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch {
    // localStorage unavailable
  }
}

const TERMINAL_STATUSES = ['completed', 'failed', 'cancelled'];

function createAppStore() {
  const store = writable({
    page: 'dashboard',
    version: '',
    devices: [],
    targets: [],
    profiles: [],
    jobs: [],
    history: [],
    stats: { overview: {}, timeline: [], scanners: [], targets: [], hourly: [] },
    loading: false,
    lastUpdated: null,
    toast: null,
    wsConnected: false,
    authRequired: false,
    settings: loadSettings()
  });
  const { subscribe, update } = store;

  const notify = (message, type = 'info') => update((s) => ({ ...s, toast: { message, type, ts: Date.now() } }));

  const loadVersion = async () => {
    try {
      const payload = await api.getVersion();
      update((s) => ({ ...s, version: payload?.version || s.version }));
    } catch {
      // Version is non-critical for the UI.
    }
  };

  const loadCore = async () => {
    update((s) => ({ ...s, loading: true }));
    try {
      const [devices, targets, profiles, jobs, history] = await Promise.all([
        api.getDevices(),
        api.getTargets(),
        api.getProfiles(),
        api.getJobs(),
        api.getHistory()
      ]);
      update((s) => ({ ...s, devices, targets, profiles, jobs, history, loading: false, lastUpdated: Date.now() }));
    } catch (error) {
      if (error.message !== 'Unauthorized') notify(error.message, 'error');
      update((s) => ({ ...s, loading: false }));
    }
  };

  const loadStats = async () => {
    try {
      const [overview, timeline, scanners, targets, hourly] = await Promise.all([
        api.getStatsOverview(),
        api.getStatsTimeline(),
        api.getStatsScanners(),
        api.getStatsTargets(),
        api.getStatsHourly()
      ]);
      update((s) => ({ ...s, stats: { overview, timeline, scanners, targets, hourly }, lastUpdated: Date.now() }));
    } catch (error) {
      if (error.message !== 'Unauthorized') notify(error.message, 'error');
    }
  };

  function upsert(list, job) {
    const index = list.findIndex((item) => item.id === job.id);
    if (index >= 0) {
      const next = [...list];
      next[index] = { ...next[index], ...job };
      return next;
    }
    return [job, ...list];
  }

  const applyJobUpdate = (job) => {
    if (!job || !job.id) return;
    update((s) => {
      const jobs = upsert(s.jobs, job);
      let history = s.history;
      const inHistory = history.some((item) => item.id === job.id);
      if (inHistory) {
        history = upsert(history, job);
      } else if (TERMINAL_STATUSES.includes(String(job.status || '').toLowerCase())) {
        history = [job, ...history];
      }
      return { ...s, jobs, history, lastUpdated: Date.now() };
    });
  };

  // --- WebSocket live updates with auto-reconnect ---
  let ws = null;
  let reconnectDelay = 1000;
  let reconnectTimer = null;
  let wsStarted = false;

  const scheduleReconnect = () => {
    if (reconnectTimer) return;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      reconnectDelay = Math.min(reconnectDelay * 2, 30000);
      connectWebSocket();
    }, reconnectDelay);
  };

  const connectWebSocket = () => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    try {
      ws = new WebSocket(`${proto}://${window.location.host}/api/v1/ws`);
    } catch {
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      reconnectDelay = 1000;
      update((s) => ({ ...s, wsConnected: true }));
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'job_update' && message.data) applyJobUpdate(message.data);
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = () => {
      ws = null;
      update((s) => ({ ...s, wsConnected: false }));
      scheduleReconnect();
    };

    ws.onerror = () => {
      try {
        ws?.close();
      } catch {
        // already closed
      }
    };
  };

  const startWebSocket = () => {
    if (wsStarted) return;
    wsStarted = true;
    connectWebSocket();
  };

  // Global 401 handling: show the login overlay.
  setUnauthorizedHandler(() => {
    update((s) => (s.authRequired ? s : { ...s, authRequired: true }));
  });

  return {
    subscribe,
    setPage: (page) => update((s) => ({ ...s, page })),
    setSettings: (partial) => update((s) => {
      const settings = { ...s.settings, ...partial };
      persistSettings(settings);
      return { ...s, settings };
    }),
    notify,
    clearToast: () => update((s) => ({ ...s, toast: null })),
    refreshAll: async () => {
      await loadVersion();
      await loadCore();
      await loadStats();
    },
    loadCore,
    loadStats,
    startWebSocket,
    applyJobUpdate,
    isWsConnected: () => get(store).wsConnected,
    activeJobCount: () => get(store).jobs.filter((j) => isActive(j.status)).length,
    setAuthRequired: (value) => update((s) => ({ ...s, authRequired: value })),
    hasToken: () => Boolean(getToken()),
    logout: () => {
      setToken(null);
      update((s) => ({ ...s, authRequired: false }));
    },
    replaceJobs: (jobs) => update((s) => ({ ...s, jobs, lastUpdated: Date.now() })),
    replaceHistory: (history) => update((s) => ({ ...s, history, lastUpdated: Date.now() })),
    replaceDevices: (devices) => update((s) => ({ ...s, devices, lastUpdated: Date.now() })),
    replaceTargets: (targets) => update((s) => ({ ...s, targets, lastUpdated: Date.now() }))
  };
}

export const appStore = createAppStore();
