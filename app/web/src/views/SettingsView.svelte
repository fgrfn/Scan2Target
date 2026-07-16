<script>
  import { onMount } from 'svelte';
  import Icon from '../components/ui/Icon.svelte';
  import { api, setToken } from '../lib/api';
  import { appStore } from '../stores/app';
  import { lang } from '../lib/i18n';
  export let settings;
  export let version = '';
  export let profiles = [];
  export let authConfig = { enabled: true };
  export let onChange = () => {};
  export let onNotify = () => {};
  export let onAuthChanged = () => {};

  let account = { username: '', email: '', current_password: '', new_password: '' };
  let savingAccount = false;
  let haOpen = false;
  let haProfile = '';
  $: if (!haProfile && profiles.length) haProfile = profiles[0].id;
  $: c = $lang === 'de' ? {
    interface: 'Oberfläche', interfaceLead: 'Sprache und Darstellung auf diesem Gerät.', language: 'Sprache', theme: 'Darstellung', system: 'System', light: 'Hell', dark: 'Dunkel',
    account: 'Anmeldung', accountLead: 'Das einzelne Administratorkonto verwalten oder den Anmeldeschutz deaktivieren.', enabled: 'Anmeldung erforderlich', user: 'Benutzername', email: 'E-Mail', current: 'Aktuelles Passwort', next: 'Neues Passwort (optional)', save: 'Konto aktualisieren', saved: 'Konto aktualisiert', authSaved: 'Anmeldeeinstellung gespeichert', logout: 'Abmelden',
    ha: 'Home Assistant', haLead: 'Die bestehende Scan-API für Taster und Automationen.', show: 'Beispiel anzeigen', hide: 'Beispiel ausblenden', copy: 'Kopieren', copied: 'Kopiert', version: 'Version', live: 'Betrieb', online: 'Online'
  } : {
    interface: 'Interface', interfaceLead: 'Language and appearance on this device.', language: 'Language', theme: 'Appearance', system: 'System', light: 'Light', dark: 'Dark',
    account: 'Sign-in', accountLead: 'Manage the single administrator account or disable sign-in protection.', enabled: 'Require sign-in', user: 'Username', email: 'Email', current: 'Current password', next: 'New password (optional)', save: 'Update account', saved: 'Account updated', authSaved: 'Sign-in setting saved', logout: 'Log out',
    ha: 'Home Assistant', haLead: 'The existing scan API for buttons and automations.', show: 'Show example', hide: 'Hide example', copy: 'Copy', copied: 'Copied', version: 'Version', live: 'Operation', online: 'Online'
  };
  $: snippet = `rest_command:\n  scan_document:\n    url: "${window.location.origin}/api/v1/homeassistant/scan"\n    method: POST\n    content_type: "application/json"\n    payload: '{"scanner_id":"favorite","target_id":"favorite","profile":"${haProfile}"}'`;

  async function toggleAuth(enabled) {
    try { await api.setAuthConfig(enabled); await onAuthChanged(); onNotify(c.authSaved, 'success'); }
    catch (error) { onNotify(error.message, 'error'); }
  }
  async function updateAccount() {
    savingAccount = true;
    try {
      const result = await api.updateAccount({ ...account, email: account.email || null, new_password: account.new_password || null });
      setToken(result.access_token); account.current_password = ''; account.new_password = ''; onNotify(c.saved, 'success'); appStore.reconnectWebSocket();
    } catch (error) { onNotify(error.message, 'error'); }
    finally { savingAccount = false; }
  }
  async function logout() { await appStore.logout(); onNotify(c.logout, 'success'); }
  async function copySnippet() { try { await navigator.clipboard.writeText(snippet); onNotify(c.copied, 'success'); } catch (error) { onNotify(error.message, 'error'); } }
  onMount(async () => {
    if (!appStore.hasToken()) return;
    try { const user = await api.getMe(); account.username = user.username || ''; account.email = user.email || ''; }
    catch { /* Account details stay editable manually if the session expired. */ }
  });
</script>

<div class="settings-grid">
  <section class="settings-card"><div class="settings-heading"><span class="settings-icon"><Icon name="settings" /></span><div><h2>{c.interface}</h2><p>{c.interfaceLead}</p></div></div>
    <div class="setting-row"><span>{c.language}</span><div class="choice-pills compact"><button class:active={$lang === 'de'} on:click={() => lang.set('de')}>Deutsch</button><button class:active={$lang === 'en'} on:click={() => lang.set('en')}>English</button></div></div>
    <div class="setting-row"><span>{c.theme}</span><select value={settings.theme} on:change={(event) => onChange({ theme: event.currentTarget.value })}><option value="system">{c.system}</option><option value="light">{c.light}</option><option value="dark">{c.dark}</option></select></div>
  </section>

  <section class="settings-card"><div class="settings-heading"><span class="settings-icon"><Icon name="logout" /></span><div><h2>{c.account}</h2><p>{c.accountLead}</p></div></div>
    <label class="switch-row"><span>{c.enabled}</span><input type="checkbox" checked={authConfig.enabled} on:change={(event) => toggleAuth(event.currentTarget.checked)} /></label>
    {#if appStore.hasToken()}<form class="account-form" on:submit|preventDefault={updateAccount}><div class="form-grid"><label>{c.user}<input bind:value={account.username} minlength="3" required /></label><label>{c.email}<input type="email" bind:value={account.email} /></label><label>{c.current}<input type="password" bind:value={account.current_password} required /></label><label>{c.next}<input type="password" bind:value={account.new_password} minlength={account.new_password ? 12 : null} /></label></div><div class="flow-actions"><button type="button" class="btn secondary" on:click={logout}>{c.logout}</button><button class="btn primary" disabled={savingAccount}>{c.save}</button></div></form>{/if}
  </section>

  <section class="settings-card full"><div class="settings-heading"><span class="settings-icon"><Icon name="bolt" /></span><div><h2>{c.ha}</h2><p>{c.haLead}</p></div></div>
    <button class="btn secondary" on:click={() => haOpen = !haOpen}>{haOpen ? c.hide : c.show}</button>
    {#if haOpen}<div class="ha-config"><select bind:value={haProfile}>{#each profiles as profile}<option value={profile.id}>{profile.name}</option>{/each}</select><pre>{snippet}</pre><button class="btn secondary" on:click={copySnippet}><Icon name="copy" size={15} />{c.copy}</button></div>{/if}
  </section>

  <section class="settings-card full system-strip"><div><span>{c.version}</span><strong>{version || '—'}</strong></div><div><span>{c.live}</span><strong class="online"><i></i>{c.online}</strong></div></section>
</div>
