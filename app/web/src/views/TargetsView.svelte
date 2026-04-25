<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import { api } from '../lib/api';
  export let data;
  export let onTargets = () => {};
  export let onNotify = () => {};

  const emptyForm = () => ({ id: '', name: '', type: 'webhook', config: { url: '' }, enabled: true, description: '' });
  let form = emptyForm();
  let editing = false;

  $: enabledCount = (data.targets || []).filter((target) => target.enabled !== false).length;

  async function reload() {
    onTargets(await api.getTargets());
  }

  function startCreate() {
    editing = false;
    form = emptyForm();
  }

  function edit(target) {
    editing = true;
    form = { ...JSON.parse(JSON.stringify(target)), config: { ...(target.config || {}) } };
  }

  async function save(validate = true) {
    try {
      if (!form.name) {
        onNotify('Target name is required', 'error');
        return;
      }
      const payload = { ...form, config: { ...(form.config || {}) } };
      if (editing) await api.updateTarget(payload.id, payload, validate);
      else {
        const id = payload.id || payload.name.toLowerCase().replace(/\s+/g, '_');
        await api.createTarget({ ...payload, id }, validate);
      }
      await reload();
      onNotify('Target saved', 'success');
      startCreate();
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function remove(id) {
    try {
      await api.deleteTarget(id);
      await reload();
      onNotify('Target removed', 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
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

<section class="grid cols-3">
  <div class="metric-card success">
    <span class="metric-label">Enabled</span>
    <strong class="metric-value">{enabledCount}</strong>
    <span class="metric-foot">Targets available for scans</span>
  </div>
  <div class="metric-card info">
    <span class="metric-label">Total</span>
    <strong class="metric-value">{data.targets.length}</strong>
    <span class="metric-foot">Configured destinations</span>
  </div>
  <div class="metric-card warning">
    <span class="metric-label">Editing</span>
    <strong class="metric-value">{editing ? '1' : '0'}</strong>
    <span class="metric-foot">Active form state</span>
  </div>
</section>

<section class="grid cols-2">
  <Card title="Targets" subtitle="Destination management with test actions" eyebrow="Routing">
    {#if !data.targets.length}
      <div class="empty-state"><div><strong>No targets configured</strong><span>Create your first scan destination on the right.</span></div></div>
    {:else}
      <div class="table-wrap">
        <table>
          <thead><tr><th>Name</th><th>Type</th><th>Enabled</th><th>Description</th><th>Actions</th></tr></thead>
          <tbody>
            {#each data.targets as target}
              <tr>
                <td><strong>{target.name}</strong></td>
                <td><Badge tone="info" text={target.type} /></td>
                <td><Badge tone={target.enabled ? 'success' : 'neutral'} text={target.enabled ? 'Enabled' : 'Disabled'} /></td>
                <td>{target.description || '-'}</td>
                <td class="row gap">
                  <button class="btn ghost" on:click={() => test(target.id)}>Test</button>
                  <button class="btn ghost" on:click={() => edit(target)}>Edit</button>
                  <button class="btn danger" on:click={() => remove(target.id)}>Remove</button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </Card>

  <Card title={editing ? 'Edit target' : 'New target'} subtitle="Validation can be bypassed for offline targets" eyebrow="Configuration">
    <div class="form-grid">
      <div class="field-grid">
        <label>ID <input bind:value={form.id} placeholder="auto from name" /></label>
        <label>Name <input bind:value={form.name} placeholder="Paperless Inbox" /></label>
      </div>
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
      <label>Description <input bind:value={form.description} placeholder="Optional description" /></label>
      <label>Connection / URL <input bind:value={form.config.url} placeholder="//nas/share or https://endpoint" /></label>
      <label class="check-field"><input type="checkbox" bind:checked={form.enabled} /> Enabled</label>
    </div>
    <div class="row gap top-gap">
      <button class="btn primary" on:click={() => save(true)}>Test & Save</button>
      <button class="btn ghost" on:click={() => save(false)}>Save without test</button>
      <button class="btn ghost" on:click={startCreate}>Reset</button>
    </div>
  </Card>
</section>
