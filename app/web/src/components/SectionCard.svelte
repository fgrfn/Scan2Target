<script>
  export let title;
  export let subtitle = '';
  export let actions = [];
</script>

<section class="section-card">
  <div class="section-heading">
    <div>
      <h2>{title}</h2>
      {#if subtitle}
        <p class="muted">{subtitle}</p>
      {/if}
    </div>
    <div class="section-actions">
      {#each actions as action}
        <button class="ghost" on:click={action.onClick}>{action.label}</button>
      {/each}
    </div>
  </div>
  <div class="section-body">
    <slot />
  </div>
</section>
