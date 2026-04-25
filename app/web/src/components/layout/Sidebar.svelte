<script>
  export let pages = [];
  export let current = 'dashboard';
  export let onNavigate = () => {};

  const iconMap = {
    dashboard: '⌘',
    'new-scan': '◉',
    'active-scans': '↻',
    devices: '▣',
    targets: '→',
    history: '◷',
    statistics: '▰',
    settings: '⚙'
  };

  $: primaryPages = pages.filter((p) => ['dashboard', 'new-scan', 'active-scans', 'history'].includes(p.id));
  $: managePages = pages.filter((p) => ['devices', 'targets', 'statistics', 'settings'].includes(p.id));
</script>

<aside class="sidebar">
  <div class="brand-card">
    <div class="logo-mark">S2</div>
    <div class="brand-text">
      <div class="logo-title">Scan2Target</div>
      <div class="logo-subtitle">Document Command Center</div>
    </div>
  </div>

  <div>
    <div class="sidebar-section-label">Workflow</div>
    <nav aria-label="Primary navigation">
      {#each primaryPages as item}
        <button class="nav-item" class:item-active={item.id === current} on:click={() => onNavigate(item.id)}>
          <span class="nav-icon">{iconMap[item.id] || '•'}</span>
          <span class="nav-label">{item.label}</span>
          <span class="nav-dot" aria-hidden="true"></span>
        </button>
      {/each}
    </nav>
  </div>

  <div>
    <div class="sidebar-section-label">Manage</div>
    <nav aria-label="Management navigation">
      {#each managePages as item}
        <button class="nav-item" class:item-active={item.id === current} on:click={() => onNavigate(item.id)}>
          <span class="nav-icon">{iconMap[item.id] || '•'}</span>
          <span class="nav-label">{item.label}</span>
          <span class="nav-dot" aria-hidden="true"></span>
        </button>
      {/each}
    </nav>
  </div>

  <div class="sidebar-footer">
    <div class="mini-panel">
      <div class="mini-panel-title">System status</div>
      <div class="mini-panel-row"><span>API</span><span class="status-dot" title="Online"></span></div>
      <div class="mini-panel-row"><span>Cache strategy</span><strong>Network first</strong></div>
    </div>
  </div>
</aside>
