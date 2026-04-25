import { writable } from 'svelte/store';
import { api } from '../lib/api';

export const pages = [
  { id: 'dashboard', label: 'Dashboard', icon: 'ri-dashboard-line' },
  { id: 'new-scan', label: 'New Scan', icon: 'ri-focus-3-line' },
  { id: 'active-scans', label: 'Active Scans', icon: 'ri-loader-4-line' },
  { id: 'devices', label: 'Devices', icon: 'ri-scanner-line' },
  { id: 'targets', label: 'Targets', icon: 'ri-send-plane-line' },
  { id: 'history', label: 'History', icon: 'ri-time-line' },
  { id: 'statistics', label: 'Statistics', icon: 'ri-bar-chart-2-line' },
  { id: 'settings', label: 'Settings', icon: 'ri-settings-3-line' }
];

function createAppStore() {
  const { subscribe, update } = writable({
    page: 'dashboard',
    devices: [],
    targets: [],
    profiles: [],
    jobs: [],
    history: [],
    stats: { overview: {}, timeline: [], scanners: [], targets: [], hourly: [] },
    loading: false,
    toast: null,
    settings: {
      autoRefresh: true,
      compactTables: false
    }
  });

  const notify = (message, type = 'info') => update((s) => ({ ...s, toast: { message, type, ts: Date.now() } }));

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
      update((s) => ({ ...s, devices, targets, profiles, jobs, history, loading: false }));
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
      update((s) => ({ ...s, stats: { overview, timeline, scanners, targets, hourly } }));
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
      await loadCore();
      await loadStats();
    },
    loadCore,
    loadStats,
    replaceJobs: (jobs) => update((s) => ({ ...s, jobs })),
    replaceHistory: (history) => update((s) => ({ ...s, history })),
    replaceDevices: (devices) => update((s) => ({ ...s, devices })),
    replaceTargets: (targets) => update((s) => ({ ...s, targets }))
  };
}

export const appStore = createAppStore();
