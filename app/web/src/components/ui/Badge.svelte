<script>
  export let tone = 'info';
  export let text = '';
</script>

<span class={`badge ${tone}`}>
  <span class="badge-dot" aria-hidden="true"></span>
  {text}<slot />
</span>
