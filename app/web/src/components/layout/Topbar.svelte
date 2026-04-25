<script>
  export let title = '';
  export let subtitle = '';
  export let lang = 'en';
  export let onLangChange = () => {};
  export let onRefresh = () => {};
</script>

<header class="topbar">
  <div>
    <h1>{title}</h1>
    <p>{subtitle}</p>
  </div>
  <div class="topbar-actions">
    <button class="btn ghost" on:click={onRefresh}>Refresh</button>
    <label>
      <span class="sr-only">Language</span>
      <select value={lang} on:change={(e) => onLangChange(e.target.value)}>
        <option value="en">English</option>
        <option value="de">Deutsch</option>
      </select>
    </label>
  </div>
</header>
