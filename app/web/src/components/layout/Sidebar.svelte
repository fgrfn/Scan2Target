<script>
  import Icon from '../ui/Icon.svelte';
  import { lang } from '../../lib/i18n';
  export let pages = [];
  export let current = 'scan';
  export let wsConnected = false;
  export let onNavigate = () => {};
  $: labels = $lang === 'de' ? { scan: 'Scannen', history: 'Verlauf', manage: 'Verwalten', settings: 'Einstellungen', ready: 'Bereit', offline: 'Offline' } : { scan: 'Scan', history: 'History', manage: 'Manage', settings: 'Settings', ready: 'Ready', offline: 'Offline' };
</script>
<aside class="sidebar">
  <button class="brand" on:click={() => onNavigate('scan')}><span class="logo-mark">S2</span><span><strong>Scan2Target</strong><small>Scan appliance</small></span></button>
  <nav aria-label="Main navigation">
    {#each pages as item}<button class:active={current === item.id} on:click={() => onNavigate(item.id)}><Icon name={item.icon} /><span>{labels[item.id]}</span></button>{/each}
  </nav>
  <div class="sidebar-status"><span class:offline={!wsConnected}></span>{wsConnected ? labels.ready : labels.offline}</div>
</aside>
