<script>
  export let cards = [];
</script>

<div class="stat-grid">
  {#each cards as card}
    <div class="stat-card">
      <div class="stat-icon">{card.icon}</div>
      <div class="stat-label">{card.label}</div>
      <div class="stat-value">{card.value}</div>
      {#if card.sub}
        <div class="stat-sub">{card.sub}</div>
      {/if}
    </div>
  {/each}
</div>
