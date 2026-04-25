<script>
  export let cards = [];
</script>

<div class="stat-grid-cards">
  {#each cards as card}
    <article class="stat-card">
      <div class="stat-card-head">
        <div class="stat-icon" aria-hidden="true">{card.icon}</div>
        <div class="stat-meta">
          <div class="stat-label">{card.label}</div>
          {#if card.sub}
            <div class="stat-sub">{card.sub}</div>
          {/if}
        </div>
      </div>
      <div class="stat-value">{card.value}</div>
    </article>
  {/each}
</div>
