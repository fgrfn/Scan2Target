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
  const unsubscribe = appStore.subscribe((value) => (state = value));

  let currentLang = 'en';
  const langUnsub = lang.subscribe((value) => (currentLang = value));

  const hashAliases = {
    scan: 'new-scan',
    newscan: 'new-scan',
    queue: 'active-scans',
    jobs: 'active-scans',
    stats: 'statistics',
    analytics: 'statistics'
  };

  $: pageMeta = pages.find((page) => page.id === state?.page) || pages[0];
  $: activeJobs = (state?.jobs || []).filter((job) => ['queued', 'running', 'waiting'].includes(job.status)).length;
  $: onlineDevices = (state?.devices || []).filter((device) => device.status === 'online').length;

  function pageFromHash() {
    const raw = window.location.hash.replace('#', '').trim();
    if (!raw) return 'dashboard';
    return hashAliases[raw] || raw;
  }

  function navigate(page) {
    appStore.setPage(page);
    if (typeof window !== 'undefined') {
      const hash = page === 'dashboard' ? '' : `#${page}`;
      history.replaceState(null, '', `${window.location.pathname}${hash}`);
    }
  }

  function applyHashRoute() {
    const page = pageFromHash();
    if (pages.some((item) => item.id === page)) appStore.setPage(page);
  }

  function notify(message, type = 'info') {
    appStore.notify(message, type);
    setTimeout(() => appStore.clearToast(), 3500);
  }

  onMount(() => {
    applyHashRoute();
    appStore.refreshAll();

    const interval = setInterval(() => {
      if (state?.settings.autoRefresh) appStore.refreshAll();
    }, 10000);

    window.addEventListener('hashchange', applyHashRoute);

    return () => {
      clearInterval(interval);
      window.removeEventListener('hashchange', applyHashRoute);
      unsubscribe();
      langUnsub();
    };
  });
</script>

<svelte:head>
  <meta name="theme-color" content="#101828" />
</svelte:head>

<div class:app-loading={state?.loading} class="app-shell">
  <Sidebar {pages} current={state.page} onNavigate={navigate} />

  <main class="main-area">
    <Topbar
      title={pageMeta.label}
      subtitle={pageMeta.description}
      lang={currentLang}
      loading={state.loading}
      activeJobs={activeJobs}
      onlineDevices={onlineDevices}
      onLangChange={(value) => lang.set(value)}
      onRefresh={appStore.refreshAll}
    />

    <div class="view-container">
      {#if state.page === 'dashboard'}
        <DashboardView data={state} onNavigate={navigate} />
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

  <BottomNav {pages} current={state.page} onNavigate={navigate} />
  <Toast toast={state.toast} onClose={appStore.clearToast} />
</div>
