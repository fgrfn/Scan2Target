<script>
  export let pages = [];
  export let current = 'dashboard';
  export let onNavigate = () => {};

  const iconMap = {
    dashboard: '⌘',
    'new-scan': '◉',
    'active-scans': '↻',
    history: '◷',
    settings: '⚙'
  };
  $: mobilePages = pages.filter((p) => ['dashboard', 'new-scan', 'active-scans', 'history', 'settings'].includes(p.id));
</script>

<nav class="bottom-nav" aria-label="Mobile navigation">
  {#each mobilePages as item}
    <button class:item-active={item.id === current} on:click={() => onNavigate(item.id)}>
      <span class="bottom-icon">{iconMap[item.id] || '•'}</span>
      <span class="bottom-label">{item.label}</span>
    </button>
  {/each}
</nav>
