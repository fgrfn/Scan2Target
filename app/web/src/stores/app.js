import { writable } from 'svelte/store';
import { api } from '../lib/api';

export const pages = [
  { id: 'dashboard', label: 'Dashboard', mobileLabel: 'Home', icon: '⌁', description: 'Live overview, quick actions and recent scan activity' },
  { id: 'new-scan', label: 'New Scan', mobileLabel: 'Scan', icon: '◎', description: 'Guided one-tap workflow from scanner to target' },
  { id: 'active-scans', label: 'Queue', mobileLabel: 'Queue', icon: '◌', description: 'Running and waiting jobs' },
  { id: 'devices', label: 'Devices', mobileLabel: 'Devices', icon: '▣', description: 'Scanner discovery, health checks and favorites' },
  { id: 'targets', label: 'Targets', mobileLabel: 'Targets', icon: '↗', description: 'SMB, Paperless, mail, SFTP, webhook and cloud destinations' },
  { id: 'history', label: 'History', mobileLabel: 'History', icon: '◷', description: 'Search, retry and clean up completed jobs' },
  { id: 'statistics', label: 'Analytics', mobileLabel: 'Stats', icon: '▥', description: 'Throughput, hourly distribution and target performance' },
  { id: 'settings', label: 'Settings', mobileLabel: 'More', icon: '⚙', description: 'Application behavior and system information' }
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
