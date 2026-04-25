<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import { api } from '../lib/api';
  export let data;
  export let onTargets = () => {};
  export let onNotify = () => {};

  let form = { id: '', name: '', type: 'webhook', config: { url: '' }, enabled: true, description: '' };
  let editing = false;

  async function reload() {
    onTargets(await api.getTargets());
  }

  function startCreate() {
    editing = false;
    form = { id: '', name: '', type: 'webhook', config: { url: '' }, enabled: true, description: '' };
  }

  function edit(target) {
    editing = true;
    form = JSON.parse(JSON.stringify(target));
  }

  async function save(validate = true) {
    try {
      if (editing) await api.updateTarget(form.id, form, validate);
      else {
        const id = form.id || form.name.toLowerCase().replace(/\s+/g, '_');
        await api.createTarget({ ...form, id }, validate);
      }
      await reload();
      onNotify('Target saved', 'success');
      startCreate();
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function remove(id) {
    await api.deleteTarget(id);
    await reload();
    onNotify('Target removed', 'success');
  }

  async function test(id) {
    try {
      const result = await api.testTarget(id);
      onNotify(result.message || 'Target reachable', 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }
</script>

<section class="grid cols-2">
  <Card title="Targets" subtitle="Destination management with test actions">
    <div class="table-wrap">
      <table>
        <thead><tr><th>Name</th><th>Type</th><th>Enabled</th><th>Actions</th></tr></thead>
        <tbody>
          {#if !data.targets.length}<tr><td colspan="4" class="muted">No targets configured.</td></tr>{/if}
          {#each data.targets as t}
            <tr>
              <td>{t.name}</td>
              <td><Badge tone="info" text={t.type} /></td>
              <td>{t.enabled ? 'Yes' : 'No'}</td>
              <td class="row gap">
                <button class="btn ghost" on:click={() => test(t.id)}>Test</button>
                <button class="btn ghost" on:click={() => edit(t)}>Edit</button>
                <button class="btn danger" on:click={() => remove(t.id)}>Remove</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </Card>

  <Card title={editing ? 'Edit target' : 'New target'} subtitle="Type badges, validation, and save">
    <label>ID <input bind:value={form.id} placeholder="auto from name" /></label>
    <label>Name <input bind:value={form.name} /></label>
    <label>Type
      <select bind:value={form.type}>
        <option value="smb">SMB</option>
        <option value="email">Email</option>
        <option value="paperless">Paperless</option>
        <option value="webhook">Webhook</option>
        <option value="sftp">SFTP</option>
        <option value="nextcloud">Nextcloud</option>
      </select>
    </label>
    <label>Description <input bind:value={form.description} /></label>
    <label>Connection / URL <input bind:value={form.config.url} placeholder="//nas/share or https://endpoint" /></label>
    <label><input type="checkbox" bind:checked={form.enabled} /> Enabled</label>
    <div class="row gap top-gap">
      <button class="btn primary" on:click={() => save(true)}>Test & Save</button>
      <button class="btn ghost" on:click={() => save(false)}>Save without test</button>
      <button class="btn ghost" on:click={startCreate}>Reset</button>
    </div>
  </Card>
</section>
