import { writable, derived } from 'svelte/store';

const dictionaries = {
  en: {
    appName: 'Scan2Target',
    dashboard: 'Dashboard',
    newScan: 'New Scan',
    activeScans: 'Active Scans',
    devices: 'Devices',
    targets: 'Targets',
    history: 'History',
    statistics: 'Statistics',
    settings: 'Settings',
    quickStart: 'Start New Scan',
    discoverDevices: 'Discover Devices',
    addTarget: 'Add Target',
    loading: 'Loading...'
  },
  de: {
    appName: 'Scan2Target',
    dashboard: 'Dashboard',
    newScan: 'Neuer Scan',
    activeScans: 'Aktive Scans',
    devices: 'Geräte',
    targets: 'Ziele',
    history: 'Verlauf',
    statistics: 'Statistiken',
    settings: 'Einstellungen',
    quickStart: 'Neuen Scan starten',
    discoverDevices: 'Geräte suchen',
    addTarget: 'Ziel hinzufügen',
    loading: 'Lädt...'
  }
};

const persisted = localStorage.getItem('scan2target_lang') || 'en';
export const lang = writable(persisted);

lang.subscribe((value) => localStorage.setItem('scan2target_lang', value));

export const t = derived(lang, ($lang) => dictionaries[$lang] || dictionaries.en);
