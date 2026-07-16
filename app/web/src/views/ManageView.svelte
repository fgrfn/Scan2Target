<script>
  import DevicesView from './DevicesView.svelte';
  import TargetsView from './TargetsView.svelte';
  import Icon from '../components/ui/Icon.svelte';
  import { api } from '../lib/api';
  import { lang } from '../lib/i18n';

  export let data;
  export let onDevices = () => {};
  export let onTargets = () => {};
  export let onNotify = () => {};
  export let onProfilesChanged = () => {};

  let tab = 'devices';
  let form = null;
  let editing = '';
  $: c = $lang === 'de'
    ? { devices: 'Scanner', targets: 'Ziele', profiles: 'Profile', title: 'Scan-Profile', lead: 'Qualität, Farbe und Papierquelle als wiederverwendbare Vorgaben.', add: 'Profil hinzufügen', name: 'Name', description: 'Beschreibung', dpi: 'Auflösung (DPI)', color: 'Farbmodus', source: 'Papierquelle', format: 'Format', batch: 'ADF-Stapel', cancel: 'Abbrechen', save: 'Speichern', deleted: 'Profil gelöscht', saved: 'Profil gespeichert' }
    : { devices: 'Scanners', targets: 'Targets', profiles: 'Profiles', title: 'Scan profiles', lead: 'Reusable presets for quality, color and paper source.', add: 'Add profile', name: 'Name', description: 'Description', dpi: 'Resolution (DPI)', color: 'Color mode', source: 'Paper source', format: 'Format', batch: 'ADF batch', cancel: 'Cancel', save: 'Save', deleted: 'Profile deleted', saved: 'Profile saved' };

  function emptyProfile() {
    return { id: '', name: '', description: '', dpi: 300, color_mode: 'Gray', paper_size: 'A4', format: 'pdf', quality: 85, source: 'Flatbed', batch_scan: false, auto_detect: true };
  }
  function create() { editing = ''; form = emptyProfile(); }
  function edit(profile) { editing = profile.id; form = { ...profile }; }
  async function save() {
    try {
      if (editing) await api.updateProfile(editing, form); else await api.createProfile(form);
      form = null; editing = ''; await onProfilesChanged(); onNotify(c.saved, 'success');
    } catch (error) { onNotify(error.message, 'error'); }
  }
  async function remove(id) {
    try { await api.deleteProfile(id); await onProfilesChanged(); onNotify(c.deleted, 'success'); }
    catch (error) { onNotify(error.message, 'error'); }
  }
</script>

<div class="manage-tabs" role="tablist">
  {#each [['devices', 'devices', c.devices], ['targets', 'targets', c.targets], ['profiles', 'settings', c.profiles]] as item}
    <button class:active={tab === item[0]} on:click={() => tab = item[0]} role="tab"><Icon name={item[1]} size={17} />{item[2]}</button>
  {/each}
</div>

{#if tab === 'devices'}
  <DevicesView {data} {onDevices} {onNotify} />
{:else if tab === 'targets'}
  <TargetsView {data} {onTargets} {onNotify} />
{:else}
  <section class="manage-section">
    <div class="section-heading"><div><h2>{c.title}</h2><p>{c.lead}</p></div><button class="btn primary" on:click={create}><Icon name="plus" size={17} />{c.add}</button></div>
    <div class="profile-list">
      {#each data.profiles || [] as profile (profile.id)}
        <article class="profile-row"><div><strong>{profile.name}</strong><span>{profile.dpi} DPI · {profile.color_mode} · {profile.source} · {(profile.format || '').toUpperCase()}</span></div><div class="row gap"><button class="icon-button" on:click={() => edit(profile)}><Icon name="edit" size={16} /></button>{#if !profile.is_builtin}<button class="icon-button danger-text" on:click={() => remove(profile.id)}><Icon name="trash" size={16} /></button>{/if}</div></article>
      {/each}
    </div>
  </section>
{/if}

{#if form}
  <div class="dialog-backdrop"><form class="dialog wide" on:submit|preventDefault={save}><h3>{c.add}</h3>
    <div class="form-grid">
      <label>ID<input bind:value={form.id} disabled={Boolean(editing)} pattern="[a-z0-9_-]{2,64}" required /></label>
      <label>{c.name}<input bind:value={form.name} required /></label>
      <label>{c.dpi}<input type="number" min="50" max="1200" bind:value={form.dpi} /></label>
      <label>{c.color}<select bind:value={form.color_mode}><option>Gray</option><option>Color</option><option>Lineart</option></select></label>
      <label>{c.source}<select bind:value={form.source}><option>Flatbed</option><option>ADF</option></select></label>
      <label>{c.format}<select bind:value={form.format}><option value="pdf">PDF</option><option value="jpeg">JPEG</option></select></label>
    </div>
    <label>{c.description}<input bind:value={form.description} /></label>
    <label class="checkbox-line"><input type="checkbox" bind:checked={form.batch_scan} />{c.batch}</label>
    <div class="flow-actions"><button type="button" class="btn secondary" on:click={() => form = null}>{c.cancel}</button><button class="btn primary">{c.save}</button></div>
  </form></div>
{/if}
