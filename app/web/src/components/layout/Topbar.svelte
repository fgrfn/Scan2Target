<script>
  import Icon from '../ui/Icon.svelte';
  import { lang, t } from '../../lib/i18n';

  export let title = '';
  export let subtitle = '';
  export let version = '';
  export let loading = false;
  export let lastUpdated = null;
  export let wsConnected = false;
  export let activeCount = 0;
  export let onRefresh = () => {};
  export let onShowActive = () => {};

  $: updatedText = lastUpdated
    ? new Date(lastUpdated).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '—';
</script>

<header class="topbar">
  <div class="topbar-title-wrap">
    <div class="eyebrow">{$t('appName')} {#if version}· v{version}{/if}</div>
    <h1>{title}</h1>
    <p>{subtitle}</p>
  </div>

  <div class="topbar-actions">
    {#if activeCount > 0}
      <button class="active-pill" on:click={onShowActive} title={$t('activeScans')}>
        <span class="pulse-dot" aria-hidden="true"></span>
        {$t('scansRunning', { n: activeCount })}
      </button>
    {/if}

    <div
      class="live-pill"
      class:offline={!wsConnected}
      role="status"
      title={wsConnected ? $t('liveConnectedHint') : $t('liveDisconnectedHint')}
    >
      <span class="live-dot" aria-hidden="true"></span>
      <span>{wsConnected ? $t('liveConnected') : $t('liveDisconnected')}</span>
      <span class="live-sync">{$t('lastSync')}: {updatedText}</span>
    </div>

    <div class="segmented" aria-label="Language">
      <button class:active={$lang === 'en'} on:click={() => lang.set('en')}>EN</button>
      <button class:active={$lang === 'de'} on:click={() => lang.set('de')}>DE</button>
    </div>

    <button class="btn primary" on:click={onRefresh} disabled={loading}>
      <Icon name="refresh" size={16} />
      {loading ? $t('syncing') : $t('refreshData')}
    </button>
  </div>
</header>
