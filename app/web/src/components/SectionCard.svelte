<script>
  export let id = '';
  export let title;
  export let subtitle = '';
  export let actions = [];
</script>

<section class="section-card" {id}>
  <header class="section-heading">
    <div class="section-title-wrap">
      <h2>{title}</h2>
      {#if subtitle}
        <p class="muted">{subtitle}</p>
      {/if}
    </div>
    {#if actions.length > 0}
      <div class="section-actions">
        {#each actions as action}
          <button class="ghost" on:click={action.onClick}>{action.label}</button>
        {/each}
      </div>
    {/if}
  </header>
  <div class="section-body">
    <slot />
  </div>
</section>
