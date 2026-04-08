<script lang="ts">
  interface Props {
    size?: 'sm' | 'md' | 'lg';
  }

  let { size = 'md' }: Props = $props();

  const px = $derived(size === 'sm' ? '16px' : size === 'lg' ? '36px' : '24px');
</script>

<span
  class="spinner"
  role="status"
  aria-label="Loading"
  style="width:{px};height:{px};"
></span>

<style>
  .spinner {
    display: inline-block;
    border: 2px solid rgba(255,255,255,0.08);
    border-top-color: #6366f1;
    border-radius: 50%;
    animation: spin 0.65s linear infinite;
    flex-shrink: 0;
  }

  @keyframes spin { to { transform: rotate(360deg); } }
</style>
