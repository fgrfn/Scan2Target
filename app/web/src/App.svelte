<script>
  import { onMount } from 'svelte';
  import { appStore, pages } from './stores/app';
  import { lang } from './lib/i18n';
  import { isActive } from './lib/status';
  import Sidebar from './components/layout/Sidebar.svelte';
  import Topbar from './components/layout/Topbar.svelte';
  import BottomNav from './components/layout/BottomNav.svelte';
  import Toast from './components/ui/Toast.svelte';
  import LoginOverlay from './components/LoginOverlay.svelte';
  import NewScanView from './views/NewScanView.svelte';
  import HistoryView from './views/HistoryView.svelte';
  import ManageView from './views/ManageView.svelte';
  import SettingsView from './views/SettingsView.svelte';

  let state;
  const unsubscribe = appStore.subscribe((value) => state = value);
  $: labels = $lang === 'de' ? {
    scan: ['Scannen', 'Ein klarer Weg vom Papier zur fertigen Datei.'], history: ['Verlauf', 'Letzte Scans und fehlgeschlagene Zustellungen.'],
    manage: ['Verwalten', 'Scanner, Ziele und Profile konfigurieren.'], settings: ['Einstellungen', 'Oberfläche, Anmeldung und Integrationen.']
  } : {
    scan: ['Scan', 'A clear path from paper to the finished file.'], history: ['History', 'Recent scans and failed deliveries.'],
    manage: ['Manage', 'Configure scanners, targets and profiles.'], settings: ['Settings', 'Interface, sign-in and integrations.']
  };
  $: pageTitle = labels[state?.page] || labels.scan;
  $: activeCount = (state?.jobs || []).filter((job) => isActive(job.status)).length;
  let toastTimer;
  $: if (state?.toast) { clearTimeout(toastTimer); toastTimer = setTimeout(appStore.clearToast, 4000); }

  onMount(() => {
    appStore.refreshAll(); appStore.startWebSocket();
    const interval = setInterval(() => { if (state?.settings.autoRefresh && !state?.wsConnected) appStore.refreshAll(); }, 15000);
    return () => { clearInterval(interval); clearTimeout(toastTimer); unsubscribe(); };
  });
</script>

<div class="app-shell" data-theme={state.settings.theme}>
  <Sidebar {pages} current={state.page} wsConnected={state.wsConnected} onNavigate={appStore.setPage} />
  <main class="main-area">
    <Topbar title={pageTitle[0]} subtitle={pageTitle[1]} loading={state.loading} {activeCount} onRefresh={appStore.refreshAll} onShowActive={() => appStore.setPage('history')} />
    <div class="view-container">
      {#if state.page === 'scan'}<NewScanView data={state} onNotify={appStore.notify} onNavigate={appStore.setPage} />
      {:else if state.page === 'history'}<HistoryView data={state} onHistory={appStore.replaceHistory} onNotify={appStore.notify} />
      {:else if state.page === 'manage'}<ManageView data={state} onDevices={appStore.replaceDevices} onTargets={appStore.replaceTargets} onNotify={appStore.notify} onProfilesChanged={appStore.loadCore} />
      {:else}<SettingsView settings={state.settings} version={state.version} lastUpdated={state.lastUpdated} profiles={state.profiles} authConfig={state.authConfig} onChange={appStore.setSettings} onNotify={appStore.notify} onAuthChanged={appStore.loadAuthConfig} />{/if}
    </div>
  </main>
  <BottomNav current={state.page} onNavigate={appStore.setPage} />
  <Toast toast={state.toast} onClose={appStore.clearToast} />
  {#if state.authRequired}<LoginOverlay />{/if}
</div>
