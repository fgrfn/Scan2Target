<script>
  export let brand = 'RaspScan';
  export let links = [];
</script>

<header class="topbar">
  <div class="brand">
    <div class="logo">📠</div>
    <div>
      <div class="brand-name">{brand}</div>
      <div class="brand-sub">Scan Hub</div>
    </div>
  </div>
  <nav class="links">
    {#each links as link}
      <a class="link" href={link.href}>{link.label}</a>
    {/each}
  </nav>
</header>
