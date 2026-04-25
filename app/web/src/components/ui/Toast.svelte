<script>
  export let toast = null;
  export let onClose = () => {};
</script>

{#if toast}
  <div class={`toast ${toast.type || 'info'}`} role="status">
    <span>{toast.message}</span>
    <button on:click={onClose} aria-label="Close">×</button>
  </div>
{/if}
