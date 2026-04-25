<script>
  export let tone = 'info';
  export let text = '';
</script>

<span class={`badge ${tone}`}>{text}<slot /></span>
