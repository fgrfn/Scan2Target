<script>
  export let pages = [];
  export let current = 'dashboard';
  export let onNavigate = () => {};
</script>

<aside class="sidebar">
  <div class="logo">Scan2Target</div>
  <nav>
    {#each pages as item}
      <button class:item-active={item.id === current} on:click={() => onNavigate(item.id)}>{item.label}</button>
    {/each}
  </nav>
</aside>
