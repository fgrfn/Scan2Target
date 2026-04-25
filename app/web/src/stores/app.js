import { writable } from 'svelte/store';
import { api } from '../lib/api';

export const pages = [
  { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
  { id: 'new-scan', label: 'New Scan', icon: 'scan' },
  { id: 'active-scans', label: 'Queue', icon: 'queue' },
  { id: 'devices', label: 'Devices', icon: 'devices' },
  { id: 'targets', label: 'Targets', icon: 'targets' },
  { id: 'history', label: 'History', icon: 'history' },
  { id: 'statistics', label: 'Analytics', icon: 'stats' },
  { id: 'settings', label: 'Settings', icon: 'settings' }
];

function createAppStore() {
  const { subscribe, update } = writable({
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
    settings: {
      autoRefresh: true,
      compactTables: false,
      glassEffects: true
    }
  });

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
      notify(error.message, 'error');
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
      notify(error.message, 'error');
    }
  };

  return {
    subscribe,
    setPage: (page) => update((s) => ({ ...s, page })),
    setSettings: (partial) => update((s) => ({ ...s, settings: { ...s.settings, ...partial } })),
    notify,
    clearToast: () => update((s) => ({ ...s, toast: null })),
    refreshAll: async () => {
      await loadVersion();
      await loadCore();
      await loadStats();
    },
    loadCore,
    loadStats,
    replaceJobs: (jobs) => update((s) => ({ ...s, jobs, lastUpdated: Date.now() })),
    replaceHistory: (history) => update((s) => ({ ...s, history, lastUpdated: Date.now() })),
    replaceDevices: (devices) => update((s) => ({ ...s, devices, lastUpdated: Date.now() })),
    replaceTargets: (targets) => update((s) => ({ ...s, targets, lastUpdated: Date.now() }))
  };
}

export const appStore = createAppStore();
