<script>
  export let pages = [];
  export let current = 'dashboard';
  export let onNavigate = () => {};
</script>

<aside class="sidebar" aria-label="Primary navigation">
  <div class="brand-card">
    <div class="brand-mark" aria-hidden="true">S2</div>
    <div>
      <div class="brand-title">Scan2Target</div>
      <div class="brand-subtitle">Document command center</div>
    </div>
  </div>

  <nav class="side-nav">
    {#each pages as item}
      <button class:item-active={item.id === current} on:click={() => onNavigate(item.id)} title={item.description}>
        <span class="nav-icon" aria-hidden="true">{item.icon}</span>
        <span class="nav-copy">
          <span>{item.label}</span>
          <small>{item.description}</small>
        </span>
      </button>
    {/each}
  </nav>

  <div class="sidebar-footer">
    <span class="pulse-dot"></span>
    <div>
      <strong>API linked</strong>
      <small>Local scan hub ready</small>
    </div>
  </div>
</aside>
