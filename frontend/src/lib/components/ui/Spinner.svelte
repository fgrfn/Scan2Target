<script lang="ts">
  interface Props {
    size?: 'sm' | 'md' | 'lg';
  }

  let { size = 'md' }: Props = $props();

  const sizes = { sm: '16px', md: '24px', lg: '36px' };
  const px = $derived(sizes[size]);
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
    border: 2px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    flex-shrink: 0;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
