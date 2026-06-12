<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import Icon from '../components/ui/Icon.svelte';
  import { api } from '../lib/api';
  import { t, lang } from '../lib/i18n';
  import { appStore } from '../stores/app';

  export let settings;
  export let version = '';
  export let lastUpdated = null;
  export let profiles = [];
  export let onChange = () => {};
  export let onNotify = () => {};
  export let onProfilesChanged = () => {};

  $: updatedText = lastUpdated ? new Date(lastUpdated).toLocaleString() : $t('notSynced');

  // --- Profile management ---
  let profileForm = null; // null = closed
  let editingProfileId = null;

  function blankProfile() {
    return {
      id: '',
      name: '',
      dpi: 300,
      color_mode: 'Gray',
      paper_size: 'A4',
      format: 'pdf',
      quality: 85,
      source: 'Flatbed',
      batch_scan: false,
      auto_detect: true,
      description: ''
    };
  }

  function openCreateProfile() {
    editingProfileId = null;
    profileForm = blankProfile();
  }

  function openEditProfile(profile) {
    editingProfileId = profile.id;
    profileForm = { ...profile };
  }

  async function saveProfile() {
    try {
      if (editingProfileId) await api.updateProfile(editingProfileId, profileForm);
      else await api.createProfile(profileForm);
      profileForm = null;
      editingProfileId = null;
      await onProfilesChanged();
      onNotify($t('profileSaved'), 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function deleteProfile(id) {
    try {
      await api.deleteProfile(id);
      await onProfilesChanged();
      onNotify($t('profileDeleted'), 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  // --- Home Assistant helper ---
  let haOpen = false;
  let haProfile = 'document_200_pdf';

  $: haSnippet = [
    'rest_command:',
    '  scan_document:',
    `    url: "${window.location.origin}/api/v1/homeassistant/scan"`,
    '    method: POST',
    '    content_type: "application/json"',
    `    payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "${haProfile}"}'`
  ].join('\n');

  async function copySnippet() {
    try {
      await navigator.clipboard.writeText(haSnippet);
      onNotify($t('copied'), 'success');
    } catch {
      onNotify($t('copyFailed'), 'error');
    }
  }

  // --- Auth ---
  const loggedIn = appStore.hasToken();

  function logout() {
    appStore.logout();
    onNotify($t('loggedOut'), 'success');
  }
</script>

<section class="grid cols-2">
  <Card title={$t('uiPrefs')} subtitle={$t('uiPrefsSub')}>
    <div class="field-label">{$t('languageLabel')}</div>
    <div class="segmented inline">
      <button class:active={$lang === 'en'} on:click={() => lang.set('en')}>English</button>
      <button class:active={$lang === 'de'} on:click={() => lang.set('de')}>Deutsch</button>
    </div>

    <label class="checkbox-line top-gap">
      <input type="checkbox" checked={settings.autoRefresh} on:change={(e) => onChange({ autoRefresh: e.target.checked })} />
      {$t('autoRefreshLabel')}
    </label>
    <label class="checkbox-line">
      <input type="checkbox" checked={settings.compactTables} on:change={(e) => onChange({ compactTables: e.target.checked })} />
      {$t('compactTablesLabel')}
    </label>

    {#if loggedIn}
      <div class="top-gap">
        <button class="btn ghost" on:click={logout}><Icon name="logout" size={16} /> {$t('logoutBtn')}</button>
      </div>
    {/if}
  </Card>

  <Card title={$t('systemInfo')} subtitle={$t('systemInfoSub')}>
    <div class="resource-meta">
      <div class="meta-box"><span>{$t('versionLabel')}</span><strong>{version || $t('unknown')}</strong></div>
      <div class="meta-box"><span>{$t('lastUpdate')}</span><strong>{updatedText}</strong></div>
      <div class="meta-box"><span>{$t('cacheStrategy')}</span><strong>{$t('networkFirst')}</strong></div>
    </div>
  </Card>
</section>

<Card title={$t('profileMgmt')} subtitle={$t('profileMgmtSub')}>
  <div slot="actions">
    <button class="btn primary" on:click={openCreateProfile}><Icon name="plus" size={16} /> {$t('newProfileBtn')}</button>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>{$t('name')}</th>
          <th>{$t('idLabel')}</th>
          <th>DPI</th>
          <th>{$t('pfColorMode')}</th>
          <th>{$t('pfFormat')}</th>
          <th>{$t('pfSource')}</th>
          <th></th>
          <th>{$t('actions')}</th>
        </tr>
      </thead>
      <tbody>
        {#each profiles as p (p.id)}
          <tr>
            <td><strong>{p.name}</strong>{#if p.description}<p class="muted small">{p.description}</p>{/if}</td>
            <td class="id-cell">{p.id}</td>
            <td>{p.dpi}</td>
            <td>{p.color_mode}</td>
            <td>{(p.format || '').toUpperCase()}</td>
            <td>{p.source}{#if p.batch_scan} · ADF{/if}</td>
            <td><Badge tone={p.is_builtin ? 'info' : 'neutral'} text={p.is_builtin ? $t('builtinBadge') : $t('customBadge')} /></td>
            <td>
              <div class="row gap">
                <button class="btn ghost small-btn" on:click={() => openEditProfile(p)}><Icon name="edit" size={14} /></button>
                {#if !p.is_builtin}
                  <button class="btn danger small-btn" on:click={() => deleteProfile(p.id)}><Icon name="trash" size={14} /></button>
                {/if}
              </div>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</Card>

<Card title={$t('haTitle')} subtitle={$t('haSub')}>
  <button class="btn ghost" on:click={() => (haOpen = !haOpen)}>
    <Icon name="bolt" size={16} /> {haOpen ? $t('haHide') : $t('haShow')}
  </button>

  {#if haOpen}
    <div class="top-gap">
      <p class="muted small">{$t('haIntro')}</p>
      <label>{$t('haProfileLabel')}
        <select bind:value={haProfile}>
          {#each profiles as p (p.id)}
            <option value={p.id}>{p.name}</option>
          {/each}
        </select>
      </label>
      <div class="code-block top-gap">
        <pre>{haSnippet}</pre>
        <button class="btn ghost small-btn code-copy" on:click={copySnippet}>
          <Icon name="copy" size={14} /> {$t('copy')}
        </button>
      </div>
      <p class="muted small">{$t('haUsage')}</p>
    </div>
  {/if}
</Card>

{#if profileForm}
  <div class="dialog-backdrop">
    <div class="dialog wide">
      <h3>{editingProfileId ? $t('editProfileTitle') : $t('createProfileTitle')}</h3>

      <div class="grid cols-2">
        <label>{$t('pfId')}
          <input bind:value={profileForm.id} placeholder={$t('pfIdPlaceholder')} disabled={Boolean(editingProfileId)} />
        </label>
        <label>{$t('pfName')} <input bind:value={profileForm.name} /></label>
      </div>
      {#if !editingProfileId}<p class="muted small">{$t('pfIdHint')}</p>{/if}

      <div class="grid cols-2">
        <label>{$t('pfDpi')} <input type="number" min="50" max="1200" bind:value={profileForm.dpi} /></label>
        <label>{$t('pfQuality')} <input type="number" min="10" max="100" bind:value={profileForm.quality} /></label>
      </div>

      <div class="grid cols-2">
        <label>{$t('pfColorMode')}
          <select bind:value={profileForm.color_mode}>
            <option value="Color">{$t('colorColor')}</option>
            <option value="Gray">{$t('colorGray')}</option>
            <option value="Lineart">{$t('colorLineart')}</option>
          </select>
        </label>
        <label>{$t('pfFormat')}
          <select bind:value={profileForm.format}>
            <option value="pdf">PDF</option>
            <option value="jpeg">JPEG</option>
          </select>
        </label>
      </div>

      <div class="grid cols-2">
        <label>{$t('pfSource')}
          <select bind:value={profileForm.source}>
            <option value="Flatbed">{$t('sourceFlatbed')}</option>
            <option value="ADF">{$t('sourceADF')}</option>
          </select>
        </label>
        <label>{$t('pfPaperSize')}
          <select bind:value={profileForm.paper_size}>
            <option value="A4">A4</option>
            <option value="A5">A5</option>
            <option value="Letter">Letter</option>
            <option value="Legal">Legal</option>
          </select>
        </label>
      </div>

      <label class="checkbox-line"><input type="checkbox" bind:checked={profileForm.batch_scan} /> {$t('pfBatch')}</label>
      <label class="checkbox-line"><input type="checkbox" bind:checked={profileForm.auto_detect} /> {$t('pfAutoDetect')}</label>
      <label>{$t('pfDescription')} <input bind:value={profileForm.description} /></label>

      <div class="row gap top-gap">
        <button class="btn ghost" on:click={() => (profileForm = null)}>{$t('cancel')}</button>
        <button class="btn primary" disabled={!profileForm.name || (!editingProfileId && !profileForm.id)} on:click={saveProfile}>
          {$t('save')}
        </button>
      </div>
    </div>
  </div>
{/if}
