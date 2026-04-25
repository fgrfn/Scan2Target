<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import { api } from '../lib/api';
  export let data;
  export let onTargets = () => {};
  export let onNotify = () => {};

  let form = { id: '', name: '', type: 'webhook', config: { url: '' }, enabled: true, description: '' };
  let editing = false;

  const targetIcons = { smb: '▤', email: '✉', paperless: '◇', webhook: '↯', sftp: '⇅', nextcloud: '☁' };

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
    if (!form.config) form.config = { url: '' };
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

<section class="grid cols-2">
  <Card title="Delivery targets" subtitle="Modern route cards for every destination.">
    <div class="resource-grid">
      {#if !data.targets.length}
        <div class="resource-card"><div class="resource-head"><div class="resource-title"><div class="resource-icon">→</div><div><h4>No targets configured</h4><p>Create your first destination route.</p></div></div><Badge tone="warning" text="empty" /></div></div>
      {/if}
      {#each data.targets as t}
        <article class="resource-card">
          <div class="resource-head">
            <div class="resource-title">
              <div class="resource-icon">{targetIcons[t.type] || '→'}</div>
              <div>
                <h4>{t.name}</h4>
                <p>{t.description || t.id}</p>
              </div>
            </div>
            <Badge tone={t.enabled === false ? 'warning' : 'success'} text={t.enabled === false ? 'disabled' : 'enabled'} />
          </div>
          <div class="resource-meta">
            <div class="meta-box"><span>Type</span><strong>{t.type}</strong></div>
            <div class="meta-box"><span>Route</span><strong>{t.config?.url || t.config?.path || '-'}</strong></div>
          </div>
          <div class="row gap">
            <button class="btn ghost" on:click={() => test(t.id)}>Test</button>
            <button class="btn ghost" on:click={() => edit(t)}>Edit</button>
            <button class="btn danger" on:click={() => remove(t.id)}>Remove</button>
          </div>
        </article>
      {/each}
    </div>
  </Card>

  <Card title={editing ? 'Edit target' : 'Create target'} subtitle="Fast form with validation-aware saving.">
    <div class="grid cols-2">
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
    <label class="checkbox-line"><input type="checkbox" bind:checked={form.enabled} /> Enabled</label>
    <div class="row gap top-gap">
      <button class="btn primary" disabled={!form.name} on:click={() => save(true)}>Test & save</button>
      <button class="btn ghost" disabled={!form.name} on:click={() => save(false)}>Save without test</button>
      <button class="btn ghost" on:click={startCreate}>Reset</button>
    </div>
  </Card>
</section>
