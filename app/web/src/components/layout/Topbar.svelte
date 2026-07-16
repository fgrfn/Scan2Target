<script>
  import Icon from '../ui/Icon.svelte';
  import { lang } from '../../lib/i18n';
  export let title = '';
  export let subtitle = '';
  export let loading = false;
  export let activeCount = 0;
  export let onRefresh = () => {};
  export let onShowActive = () => {};
  $: refresh = $lang === 'de' ? 'Aktualisieren' : 'Refresh';
</script>
<header class="topbar">
  <div><h1>{title}</h1>{#if subtitle}<p>{subtitle}</p>{/if}</div>
  <div class="topbar-actions">
    {#if activeCount}<button class="active-job" on:click={onShowActive}><span></span>{activeCount}</button>{/if}
    <button class="icon-button" title={refresh} disabled={loading} on:click={onRefresh}><Icon name="refresh" size={18} /></button>
  </div>
</header>
