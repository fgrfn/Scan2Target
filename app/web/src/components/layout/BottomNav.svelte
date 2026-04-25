<script>
  export let pages = [];
  export let current = 'dashboard';
  export let onNavigate = () => {};
  const mobilePages = pages.filter((p) => ['dashboard', 'new-scan', 'active-scans', 'history', 'settings'].includes(p.id));
</script>

<nav class="bottom-nav">
  {#each mobilePages as item}
    <button class:item-active={item.id === current} on:click={() => onNavigate(item.id)}>{item.label}</button>
  {/each}
</nav>
