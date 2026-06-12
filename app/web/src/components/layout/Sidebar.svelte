<script>
  import Icon from '../ui/Icon.svelte';
  import { t } from '../../lib/i18n';

  export let pages = [];
  export let current = 'dashboard';
  export let wsConnected = false;
  export let onNavigate = () => {};

  const labelKeys = {
    dashboard: 'dashboard',
    'new-scan': 'newScan',
    history: 'history',
    devices: 'devices',
    targets: 'targets',
    statistics: 'statistics',
    settings: 'settings'
  };

  $: scanPages = pages.filter((p) => p.group === 'scan');
  $: managePages = pages.filter((p) => p.group === 'manage');
</script>

<aside class="sidebar">
  <div class="brand-card">
    <div class="logo-mark">S2</div>
    <div class="brand-text">
      <div class="logo-title">{$t('appName')}</div>
      <div class="logo-subtitle">{$t('appTagline')}</div>
    </div>
  </div>

  <div>
    <div class="sidebar-section-label">{$t('navScan')}</div>
    <nav aria-label={$t('navScan')}>
      {#each scanPages as item}
        <button class="nav-item" class:item-active={item.id === current} on:click={() => onNavigate(item.id)}>
          <span class="nav-icon"><Icon name={item.icon} /></span>
          <span class="nav-label">{$t(labelKeys[item.id] || item.id)}</span>
          <span class="nav-dot" aria-hidden="true"></span>
        </button>
      {/each}
    </nav>
  </div>

  <div>
    <div class="sidebar-section-label">{$t('navManage')}</div>
    <nav aria-label={$t('navManage')}>
      {#each managePages as item}
        <button class="nav-item" class:item-active={item.id === current} on:click={() => onNavigate(item.id)}>
          <span class="nav-icon"><Icon name={item.icon} /></span>
          <span class="nav-label">{$t(labelKeys[item.id] || item.id)}</span>
          <span class="nav-dot" aria-hidden="true"></span>
        </button>
      {/each}
    </nav>
  </div>

  <div class="sidebar-footer">
    <div class="mini-panel">
      <div class="mini-panel-row">
        <span>{wsConnected ? $t('liveConnectedHint') : $t('liveDisconnectedHint')}</span>
        <span class="status-dot" class:offline={!wsConnected}></span>
      </div>
    </div>
  </div>
</aside>
