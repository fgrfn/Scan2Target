<script>
  import { onMount } from 'svelte';
  import { appStore, pages } from './stores/app';
  import { t } from './lib/i18n';
  import { isActive } from './lib/status';

  import Sidebar from './components/layout/Sidebar.svelte';
  import Topbar from './components/layout/Topbar.svelte';
  import BottomNav from './components/layout/BottomNav.svelte';
  import Toast from './components/ui/Toast.svelte';
  import LoginOverlay from './components/LoginOverlay.svelte';

  import DashboardView from './views/DashboardView.svelte';
  import NewScanView from './views/NewScanView.svelte';
  import DevicesView from './views/DevicesView.svelte';
  import TargetsView from './views/TargetsView.svelte';
  import HistoryView from './views/HistoryView.svelte';
  import StatisticsView from './views/StatisticsView.svelte';
  import SettingsView from './views/SettingsView.svelte';

  let state;
  const unsubscribe = appStore.subscribe((v) => (state = v));

  const titleKeys = {
    dashboard: ['dashboard', 'subDashboard'],
    'new-scan': ['newScan', 'subNewScan'],
    history: ['history', 'subHistory'],
    devices: ['devices', 'subDevices'],
    targets: ['targets', 'subTargets'],
    statistics: ['statistics', 'subStatistics'],
    settings: ['settings', 'subSettings']
  };

  $: [titleKey, subtitleKey] = titleKeys[state?.page] || titleKeys.dashboard;
  $: activeCount = (state?.jobs || []).filter((j) => isActive(j.status)).length;

  let toastTimer = null;
  $: if (state?.toast) {
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => appStore.clearToast(), 4000);
  }

  onMount(() => {
    appStore.refreshAll();
    appStore.startWebSocket();

    // Polling is only a fallback while the WebSocket is disconnected.
    const interval = setInterval(() => {
      if (state?.settings.autoRefresh && !state?.wsConnected) appStore.refreshAll();
    }, 15000);

    return () => {
      clearInterval(interval);
      clearTimeout(toastTimer);
      unsubscribe();
    };
  });
</script>

<div class="app-shell" class:compact={state.settings.compactTables}>
  <Sidebar {pages} current={state.page} wsConnected={state.wsConnected} onNavigate={appStore.setPage} />

  <main class="main-area">
    <Topbar
      title={$t(titleKey)}
      subtitle={$t(subtitleKey)}
      version={state.version}
      loading={state.loading}
      lastUpdated={state.lastUpdated}
      wsConnected={state.wsConnected}
      {activeCount}
      onRefresh={appStore.refreshAll}
      onShowActive={() => appStore.setPage('dashboard')}
    />

    <div class="view-container">
      {#if state.page === 'dashboard'}
        <DashboardView data={state} onNavigate={appStore.setPage} onNotify={appStore.notify} />
      {:else if state.page === 'new-scan'}
        <NewScanView data={state} onNotify={appStore.notify} onNavigate={appStore.setPage} />
      {:else if state.page === 'devices'}
        <DevicesView data={state} onDevices={appStore.replaceDevices} onNotify={appStore.notify} />
      {:else if state.page === 'targets'}
        <TargetsView data={state} onTargets={appStore.replaceTargets} onNotify={appStore.notify} />
      {:else if state.page === 'history'}
        <HistoryView data={state} onHistory={appStore.replaceHistory} onNotify={appStore.notify} />
      {:else if state.page === 'statistics'}
        <StatisticsView data={state} />
      {:else if state.page === 'settings'}
        <SettingsView
          settings={state.settings}
          version={state.version}
          lastUpdated={state.lastUpdated}
          profiles={state.profiles}
          onChange={appStore.setSettings}
          onNotify={appStore.notify}
          onProfilesChanged={appStore.loadCore}
        />
      {/if}
    </div>
  </main>

  <BottomNav current={state.page} onNavigate={appStore.setPage} />
  <Toast toast={state.toast} onClose={appStore.clearToast} />

  {#if state.authRequired}
    <LoginOverlay />
  {/if}
</div>
