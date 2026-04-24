<script>
  export let brand = 'Scan2Target';
  export let links = [];
  export let currentLang = 'en';
  export let onLanguageChange = () => {};
  export let version = '';

  const getCurrentHash = () => (typeof window !== 'undefined' ? window.location.hash : '#dashboard');
  let currentHash = getCurrentHash();

  if (typeof window !== 'undefined') {
    window.addEventListener('hashchange', () => {
      currentHash = getCurrentHash();
    });
  }
</script>

<header class="topbar">
  <div class="brand">
    <div class="logo">📠</div>
    <div>
      <div class="brand-name">{brand}</div>
      <div class="brand-sub">Scan Hub {version ? `v${version}` : ''}</div>
    </div>
  </div>

  <nav class="links" aria-label="Primary">
    {#each links as link}
      <a class="link {currentHash === link.href ? 'active' : ''}" href={link.href}>{link.label}</a>
    {/each}
  </nav>

  <div class="toolbar">
    <label for="lang-select" class="sr-only">Language</label>
    <select
      id="lang-select"
      class="lang-select"
      bind:value={currentLang}
      on:change={(e) => onLanguageChange(e.target.value)}
    >
      <option value="en">🇬🇧 EN</option>
      <option value="de">🇩🇪 DE</option>
    </select>
  </div>
</header>
