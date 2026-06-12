<script>
  import Icon from '../ui/Icon.svelte';
  import { t } from '../../lib/i18n';

  export let current = 'dashboard';
  export let onNavigate = () => {};

  const mainItems = [
    { id: 'dashboard', icon: 'dashboard', key: 'dashboard' },
    { id: 'new-scan', icon: 'scan', key: 'newScan' },
    { id: 'history', icon: 'history', key: 'history' },
    { id: 'settings', icon: 'settings', key: 'settings' }
  ];

  const moreItems = [
    { id: 'devices', icon: 'devices', key: 'devices' },
    { id: 'targets', icon: 'targets', key: 'targets' },
    { id: 'statistics', icon: 'stats', key: 'statistics' }
  ];

  let moreOpen = false;

  $: moreActive = moreItems.some((item) => item.id === current);

  function navigate(id) {
    moreOpen = false;
    onNavigate(id);
  }
</script>

{#if moreOpen}
  <button class="sheet-backdrop" aria-label={$t('close')} on:click={() => (moreOpen = false)}></button>
  <div class="more-sheet" role="menu" aria-label={$t('navMore')}>
    {#each moreItems as item}
      <button class="more-item" class:item-active={item.id === current} role="menuitem" on:click={() => navigate(item.id)}>
        <Icon name={item.icon} />
        <span>{$t(item.key)}</span>
      </button>
    {/each}
  </div>
{/if}

<nav class="bottom-nav" aria-label="Mobile navigation">
  {#each mainItems as item}
    <button class:item-active={item.id === current && !moreOpen} on:click={() => navigate(item.id)}>
      <span class="bottom-icon"><Icon name={item.icon} /></span>
      <span class="bottom-label">{$t(item.key)}</span>
    </button>
  {/each}
  <button class:item-active={moreActive || moreOpen} on:click={() => (moreOpen = !moreOpen)} aria-expanded={moreOpen}>
    <span class="bottom-icon"><Icon name="more" /></span>
    <span class="bottom-label">{$t('navMore')}</span>
  </button>
</nav>
