<script>
  export let title = '';
  export let subtitle = '';
  export let lang = 'en';
  export let loading = false;
  export let activeJobs = 0;
  export let onlineDevices = 0;
  export let onLangChange = () => {};
  export let onRefresh = () => {};
</script>

<header class="topbar">
  <div class="topbar-title">
    <span class="eyebrow">Scan2Target Control</span>
    <h1>{title}</h1>
    <p>{subtitle}</p>
  </div>

  <div class="topbar-actions">
    <div class="topbar-pill" title="Online scanners">
      <span class="status-dot online"></span>
      <span>{onlineDevices} online</span>
    </div>
    <div class="topbar-pill" title="Active scan jobs">
      <span class="status-dot busy"></span>
      <span>{activeJobs} jobs</span>
    </div>

    <button class="btn refresh-btn" class:spinning={loading} on:click={onRefresh} aria-label="Refresh data">
      <span aria-hidden="true">↻</span>
      <span>Refresh</span>
    </button>

    <label class="language-select">
      <span class="sr-only">Language</span>
      <select value={lang} on:change={(e) => onLangChange(e.target.value)}>
        <option value="en">EN</option>
        <option value="de">DE</option>
      </select>
    </label>
  </div>
</header>
