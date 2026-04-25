<script>
  export let title = '';
  export let subtitle = '';
  export let lang = 'en';
  export let version = '';
  export let loading = false;
  export let lastUpdated = null;
  export let onLangChange = () => {};
  export let onRefresh = () => {};

  $: updatedText = lastUpdated
    ? new Date(lastUpdated).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '—';
</script>

<header class="topbar">
  <div class="topbar-title-wrap">
    <div class="eyebrow">Scan2Target {#if version}· v{version}{/if}</div>
    <h1>{title}</h1>
    <p>{subtitle}</p>
  </div>

  <div class="topbar-actions">
    <div class="command-field" role="status" aria-live="polite">
      <span>Last sync: {updatedText}</span>
      <span class="command-kbd">⌘ K</span>
    </div>

    <div class="segmented" aria-label="Language switcher">
      <button class:active={lang === 'en'} on:click={() => onLangChange('en')}>EN</button>
      <button class:active={lang === 'de'} on:click={() => onLangChange('de')}>DE</button>
    </div>

    <button class="btn primary" on:click={onRefresh} disabled={loading}>
      {loading ? 'Syncing…' : 'Refresh data'}
    </button>
  </div>
</header>
