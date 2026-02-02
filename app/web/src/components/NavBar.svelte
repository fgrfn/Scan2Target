<script>
  export let brand = 'Scan2Target';
  export let links = [];
  export let currentLang = 'en';
  export let onLanguageChange = () => {};
  export let version = '';
</script>

<header class="topbar">
  <div class="brand">
    <div class="logo">📠</div>
    <div>
      <div class="brand-name">{brand}</div>
      <div class="brand-sub">Scan Hub {version ? `v${version}` : ''}</div>
    </div>
  </div>
  <nav class="links">
    {#each links as link}
      <a class="link" href={link.href}>{link.label}</a>
    {/each}
    <select 
      bind:value={currentLang} 
      on:change={(e) => onLanguageChange(e.target.value)}
      style="margin-left: 1rem; padding: 0.4rem 0.75rem; background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 6px; color: white; font-size: 0.875rem; cursor: pointer; backdrop-filter: blur(10px);"
    >
      <option value="en" style="background: #1a1a2e; color: white;">🇬🇧 EN</option>
      <option value="de" style="background: #1a1a2e; color: white;">🇩🇪 DE</option>
    </select>
  </nav>
</header>
