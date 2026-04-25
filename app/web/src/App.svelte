<script>
  import { onMount } from 'svelte';
  import { appStore, pages } from './stores/app';
  import { lang } from './lib/i18n';

  import Sidebar from './components/layout/Sidebar.svelte';
  import Topbar from './components/layout/Topbar.svelte';
  import BottomNav from './components/layout/BottomNav.svelte';
  import Toast from './components/ui/Toast.svelte';

  import DashboardView from './views/DashboardView.svelte';
  import NewScanView from './views/NewScanView.svelte';
  import ActiveScansView from './views/ActiveScansView.svelte';
  import DevicesView from './views/DevicesView.svelte';
  import TargetsView from './views/TargetsView.svelte';
  import HistoryView from './views/HistoryView.svelte';
  import StatisticsView from './views/StatisticsView.svelte';
  import SettingsView from './views/SettingsView.svelte';

  let state;
  const unsubscribe = appStore.subscribe((v) => (state = v));
  let currentLang = 'en';
  const langUnsub = lang.subscribe((v) => (currentLang = v));

  $: pageMeta = pages.find((p) => p.id === state?.page) || pages[0];

  onMount(async () => {
    await appStore.refreshAll();
    const interval = setInterval(async () => {
      if (state?.settings.autoRefresh) await appStore.refreshAll();
    }, 10000);

    return () => {
      clearInterval(interval);
      unsubscribe();
      langUnsub();
    };
  });

  function notify(message, type = 'info') {
    appStore.notify(message, type);
    setTimeout(() => appStore.clearToast(), 3500);
  }
</script>

<div class="app-shell">
  <Sidebar {pages} current={state.page} onNavigate={appStore.setPage} />
  <main class="main-area">
    <Topbar
      title={pageMeta.label}
      subtitle="Modern scanning control center"
      lang={currentLang}
      onLangChange={(value) => lang.set(value)}
      onRefresh={appStore.refreshAll}
    />

    <div class="view-container">
      {#if state.page === 'dashboard'}
        <DashboardView data={state} onNavigate={appStore.setPage} />
      {:else if state.page === 'new-scan'}
        <NewScanView data={state} onDone={notify} />
      {:else if state.page === 'active-scans'}
        <ActiveScansView data={state} onNotify={notify} />
      {:else if state.page === 'devices'}
        <DevicesView data={state} onDevices={appStore.replaceDevices} onNotify={notify} />
      {:else if state.page === 'targets'}
        <TargetsView data={state} onTargets={appStore.replaceTargets} onNotify={notify} />
      {:else if state.page === 'history'}
        <HistoryView data={state} onHistory={appStore.replaceHistory} onNotify={notify} />
      {:else if state.page === 'statistics'}
        <StatisticsView data={state} />
      {:else if state.page === 'settings'}
        <SettingsView settings={state.settings} onChange={appStore.setSettings} />
      {/if}
    </div>
  </main>

  <BottomNav {pages} current={state.page} onNavigate={appStore.setPage} />
  <Toast toast={state.toast} onClose={appStore.clearToast} />
</div>
