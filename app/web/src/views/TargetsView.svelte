<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import { api } from '../lib/api';

  export let data;
  export let onTargets = () => {};
  export let onNotify = () => {};

  const targetIcons = { smb: '▤', email: '✉', paperless: '◇', webhook: '↯', sftp: '⇅', nextcloud: '☁' };

  const defaultConfigByType = {
    smb: { connection: '', username: '', password: '' },
    sftp: { host: '', port: 22, username: '', password: '', remote_path: '.' },
    email: { connection: '', smtp_host: '', smtp_port: 587, username: '', password: '', use_tls: true, from: '' },
    paperless: { connection: '', api_token: '' },
    webhook: { connection: '' },
    nextcloud: { webdav_url: '', username: '', password: '', remote_path: '' }
  };

  let form = {
    id: '',
    name: '',
    type: 'webhook',
    config: JSON.parse(JSON.stringify(defaultConfigByType.webhook)),
    enabled: true,
    description: ''
  };
  let editing = false;


  async function reload() {
    onTargets(await api.getTargets());
  }

  function withTypeDefaults(type, config = {}) {
    return { ...(defaultConfigByType[type] || {}), ...(config || {}) };
  }

  function startCreate() {
    editing = false;
    form = {
      id: '',
      name: '',
      type: 'webhook',
      config: JSON.parse(JSON.stringify(defaultConfigByType.webhook)),
      enabled: true,
      description: ''
    };
  }

  function onTypeChange(nextType) {
    form = {
      ...form,
      type: nextType,
      config: withTypeDefaults(nextType, form.config)
    };
  }

  function edit(target) {
    editing = true;
    const normalizedType = (target.type || 'webhook').toLowerCase();
    const incomingConfig = target.config || {};

    // Backward compatibility for older UI/backend key names.
    if (normalizedType === 'webhook' && incomingConfig.url && !incomingConfig.connection) {
      incomingConfig.connection = incomingConfig.url;
    }
    if (normalizedType === 'smb' && incomingConfig.path && !incomingConfig.connection) {
      incomingConfig.connection = incomingConfig.path;
    }

    form = {
      ...target,
      type: normalizedType,
      config: withTypeDefaults(normalizedType, incomingConfig)
    };
  }

  function getPayload() {
    const id = form.id || form.name.toLowerCase().replace(/\s+/g, '_');
    const payload = {
      ...form,
      id,
      type: form.type,
      config: { ...form.config }
    };

    if (payload.type === 'webhook' && payload.config.url && !payload.config.connection) {
      payload.config.connection = payload.config.url;
    }

    return payload;
  }

  async function save(validate = true) {
    try {
      const payload = getPayload();
      if (editing) await api.updateTarget(form.id, payload, validate);
      else await api.createTarget(payload, validate);
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
              <div class="resource-icon">{targetIcons[(t.type || '').toLowerCase()] || '→'}</div>
              <div>
                <h4>{t.name}</h4>
                <p>{t.description || t.id}</p>
              </div>
            </div>
            <Badge tone={t.enabled === false ? 'warning' : 'success'} text={t.enabled === false ? 'disabled' : 'enabled'} />
          </div>
          <div class="resource-meta">
            <div class="meta-box"><span>Type</span><strong>{(t.type || '-').toUpperCase()}</strong></div>
            <div class="meta-box"><span>Route</span><strong>{t.config?.connection || t.config?.webdav_url || t.config?.host || '-'}</strong></div>
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

  <Card title={editing ? 'Edit target' : 'Create target'} subtitle="Validation-aware target form with auth fields.">
    <div class="grid cols-2">
      <label>ID <input bind:value={form.id} placeholder="auto from name" /></label>
      <label>Name <input bind:value={form.name} placeholder="Paperless Inbox" /></label>
    </div>

    <label>Type
      <select bind:value={form.type} on:change={(e) => onTypeChange(e.target.value)}>
        <option value="smb">SMB / CIFS</option>
        <option value="email">Email</option>
        <option value="paperless">Paperless</option>
        <option value="webhook">Webhook</option>
        <option value="sftp">SFTP</option>
        <option value="nextcloud">Nextcloud</option>
      </select>
    </label>

    <label>Description <input bind:value={form.description} placeholder="Optional description" /></label>

    {#if form.type === 'smb'}
      <div class="grid cols-2">
        <label>SMB Path <input bind:value={form.config.connection} placeholder="//nas/share/folder" /></label>
        <label>Username <input bind:value={form.config.username} placeholder="scanuser" /></label>
      </div>
      <label>Password <input type="password" bind:value={form.config.password} placeholder="••••••••" /></label>
    {:else if form.type === 'webhook'}
      <label>Webhook URL <input bind:value={form.config.connection} placeholder="https://endpoint.example/webhook" /></label>
    {:else if form.type === 'paperless'}
      <label>Paperless URL <input bind:value={form.config.connection} placeholder="https://paperless.example" /></label>
      <label>API Token <input type="password" bind:value={form.config.api_token} placeholder="Paperless API token" /></label>
    {:else if form.type === 'sftp'}
      <div class="grid cols-2">
        <label>Host <input bind:value={form.config.host} placeholder="sftp.example.local" /></label>
        <label>Port <input type="number" min="1" max="65535" bind:value={form.config.port} /></label>
      </div>
      <div class="grid cols-2">
        <label>Username <input bind:value={form.config.username} placeholder="scanner" /></label>
        <label>Password <input type="password" bind:value={form.config.password} placeholder="optional" /></label>
      </div>
      <label>Remote Path <input bind:value={form.config.remote_path} placeholder="/inbox/scans" /></label>
    {:else if form.type === 'email'}
      <label>Recipient Email <input bind:value={form.config.connection} placeholder="scan-inbox@example.com" /></label>
      <div class="grid cols-2">
        <label>SMTP Host <input bind:value={form.config.smtp_host} placeholder="smtp.example.com" /></label>
        <label>SMTP Port <input type="number" min="1" max="65535" bind:value={form.config.smtp_port} /></label>
      </div>
      <div class="grid cols-2">
        <label>SMTP Username <input bind:value={form.config.username} placeholder="optional" /></label>
        <label>SMTP Password <input type="password" bind:value={form.config.password} placeholder="optional" /></label>
      </div>
      <label>From Address <input bind:value={form.config.from} placeholder="scan2target@example.com" /></label>
      <label class="checkbox-line"><input type="checkbox" bind:checked={form.config.use_tls} /> Use TLS</label>
    {:else if form.type === 'nextcloud'}
      <label>WebDAV URL <input bind:value={form.config.webdav_url} placeholder="https://nextcloud.example/remote.php/dav/files/user" /></label>
      <div class="grid cols-2">
        <label>Username <input bind:value={form.config.username} placeholder="nextcloud-user" /></label>
        <label>Password <input type="password" bind:value={form.config.password} placeholder="App password" /></label>
      </div>
      <label>Remote Path <input bind:value={form.config.remote_path} placeholder="Documents/Scans" /></label>
    {:else}
      <label>Connection <input bind:value={form.config.connection} placeholder="Connection value" /></label>
    {/if}

    <label class="checkbox-line"><input type="checkbox" bind:checked={form.enabled} /> Enabled</label>

    <div class="row gap top-gap">
      <button class="btn primary" disabled={!form.name} on:click={() => save(true)}>Test & save</button>
      <button class="btn ghost" disabled={!form.name} on:click={() => save(false)}>Save without test</button>
      <button class="btn ghost" on:click={startCreate}>Reset</button>
    </div>
  </Card>
</section>
