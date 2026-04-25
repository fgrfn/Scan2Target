<script>
  export let pages = [];
  export let current = 'dashboard';
  export let onNavigate = () => {};
  $: mobilePages = pages.filter((page) => ['dashboard', 'new-scan', 'active-scans', 'history', 'settings'].includes(page.id));
</script>

<nav class="bottom-nav" aria-label="Mobile navigation">
  {#each mobilePages as item}
    <button class:item-active={item.id === current} on:click={() => onNavigate(item.id)}>
      <span aria-hidden="true">{item.icon}</span>
      <small>{item.mobileLabel || item.label}</small>
    </button>
  {/each}
</nav>
