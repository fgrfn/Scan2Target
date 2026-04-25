<script>
  export let title = '';
  export let subtitle = '';
  export let eyebrow = '';
  export let variant = '';
</script>

<section class={`card ${variant}`}>
  {#if title || eyebrow}
    <header class="card-head">
      <div>
        {#if eyebrow}<span class="eyebrow">{eyebrow}</span>{/if}
        {#if title}<h3>{title}</h3>{/if}
        {#if subtitle}<p>{subtitle}</p>{/if}
      </div>
      <slot name="actions" />
    </header>
  {/if}
  <div class="card-body"><slot /></div>
</section>
