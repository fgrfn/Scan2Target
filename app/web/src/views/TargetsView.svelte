<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import Icon from '../components/ui/Icon.svelte';
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';

  export let data;
  export let onTargets = () => {};
  export let onNotify = () => {};

  const defaultConfigByType = {
    smb: { connection: '', username: '', password: '' },
    sftp: { host: '', port: 22, username: '', password: '', remote_path: '.' },
    email: { connection: '', smtp_host: '', smtp_port: 587, username: '', password: '', use_tls: true, from: '' },
    paperless: { connection: '', api_token: '' },
    webhook: { connection: '' },
    nextcloud: { webdav_url: '', username: '', password: '', remote_path: '' }
  };

  function emptyForm() {
    return {
      id: '',
      name: '',
      type: 'smb',
      config: JSON.parse(JSON.stringify(defaultConfigByType.smb)),
      enabled: true,
      is_favorite: false,
      description: ''
    };
  }

  let form = emptyForm();
  let editing = false;

  async function reload() {
    onTargets(await api.getTargets());
  }

  function withTypeDefaults(type, config = {}) {
    return { ...(defaultConfigByType[type] || {}), ...(config || {}) };
  }

  function startCreate() {
    editing = false;
    form = emptyForm();
  }

  function onTypeChange(nextType) {
    form = { ...form, type: nextType, config: withTypeDefaults(nextType, form.config) };
  }

  function edit(target) {
    editing = true;
    const normalizedType = (target.type || 'webhook').toLowerCase();
    const incomingConfig = { ...(target.config || {}) };

    // Backward compatibility for older UI/backend key names.
    if (normalizedType === 'webhook' && incomingConfig.url && !incomingConfig.connection) {
      incomingConfig.connection = incomingConfig.url;
    }
    if (normalizedType === 'smb' && incomingConfig.path && !incomingConfig.connection) {
      incomingConfig.connection = incomingConfig.path;
    }

    form = {
      ...target,
      is_favorite: Boolean(target.is_favorite),
      type: normalizedType,
      config: withTypeDefaults(normalizedType, incomingConfig)
    };
  }

  function getPayload() {
    const id = form.id || form.name.toLowerCase().replace(/\s+/g, '_');
    const payload = { ...form, id, config: { ...form.config } };
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
      onNotify($t('targetSaved'), 'success');
      startCreate();
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function remove(id) {
    try {
      await api.deleteTarget(id);
      await reload();
      onNotify($t('targetRemoved'), 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function test(id) {
    try {
      const result = await api.testTarget(id);
      onNotify(result.message || $t('targetReachable'), 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function toggleFavorite(target) {
    try {
      await api.updateTarget(target.id, { ...target, is_favorite: !target.is_favorite }, false);
      await reload();
      onNotify(target.is_favorite ? $t('favoriteUnset') : $t('favoriteSet'), 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function toggleEnabled(target) {
    try {
      await api.updateTarget(target.id, { ...target, enabled: target.enabled === false }, false);
      await reload();
      onNotify(target.enabled === false ? $t('targetEnabledMsg') : $t('targetDisabledMsg'), 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }
</script>

<section class="grid cols-2">
  <Card title={$t('targetList')} subtitle={$t('targetListSub')}>
    {#if !(data.targets || []).length}
      <div class="empty-state">
        <Icon name="targets" size={28} />
        <strong>{$t('noTargets')}</strong>
        <p class="muted small">{$t('noTargetsHint')}</p>
      </div>
    {:else}
      <div class="resource-grid">
        {#each data.targets as tg (tg.id)}
          <article class="resource-card" class:dimmed={tg.enabled === false}>
            <div class="resource-head">
              <div class="resource-title">
                <div class="resource-icon"><Icon name="targets" /></div>
                <div>
                  <h4>{tg.name}</h4>
                  <p class="truncate">{tg.description || tg.id}</p>
                </div>
              </div>
              <div class="row gap center">
                <button
                  class="icon-btn"
                  class:fav-active={tg.is_favorite}
                  title={tg.is_favorite ? $t('unsetFavorite') : $t('setFavorite')}
                  on:click={() => toggleFavorite(tg)}
                >
                  <Icon name="star" size={16} filled={tg.is_favorite} />
                </button>
                <Badge
                  tone={tg.enabled === false ? 'warning' : 'success'}
                  text={tg.enabled === false ? $t('disabled') : $t('enabled')}
                />
              </div>
            </div>
            <div class="resource-meta">
              <div class="meta-box"><span>{$t('type')}</span><strong>{(tg.type || '—').toUpperCase()}</strong></div>
              <div class="meta-box">
                <span>{$t('routeLabel')}</span>
                <strong class="truncate">{tg.config?.connection || tg.config?.webdav_url || tg.config?.host || '—'}</strong>
              </div>
            </div>
            <div class="row gap wrap">
              <button class="btn ghost" on:click={() => test(tg.id)}>{$t('test')}</button>
              <button class="btn ghost" on:click={() => edit(tg)}>{$t('edit')}</button>
              <button class="btn ghost" on:click={() => toggleEnabled(tg)}>
                {tg.enabled === false ? $t('enableTarget') : $t('disableTarget')}
              </button>
              <button class="btn danger" on:click={() => remove(tg.id)}>{$t('delete')}</button>
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </Card>

  <Card title={editing ? $t('editTarget') : $t('createTarget')} subtitle={$t('targetFormSub')}>
    <div class="grid cols-2">
      <label>{$t('idLabel')} <input bind:value={form.id} placeholder={$t('tfIdPlaceholder')} disabled={editing} /></label>
      <label>{$t('name')} <input bind:value={form.name} placeholder="Paperless Inbox" /></label>
    </div>

    <label>{$t('type')}
      <select bind:value={form.type} on:change={(e) => onTypeChange(e.target.value)}>
        <option value="smb">SMB / CIFS</option>
        <option value="sftp">SFTP</option>
        <option value="email">Email</option>
        <option value="paperless">Paperless-ngx</option>
        <option value="webhook">Webhook</option>
        <option value="nextcloud">Nextcloud</option>
      </select>
    </label>

    <label>{$t('tfDescription')} <input bind:value={form.description} placeholder={$t('tfDescriptionPlaceholder')} /></label>

    {#if form.type === 'smb'}
      <div class="grid cols-2">
        <label>{$t('smbPath')} <input bind:value={form.config.connection} placeholder="//nas/share/folder" /></label>
        <label>{$t('username')} <input bind:value={form.config.username} placeholder="scanuser" /></label>
      </div>
      <label>{$t('password')} <input type="password" bind:value={form.config.password} placeholder="••••••••" /></label>
    {:else if form.type === 'webhook'}
      <label>{$t('webhookUrl')} <input bind:value={form.config.connection} placeholder="https://endpoint.example/webhook" /></label>
    {:else if form.type === 'paperless'}
      <label>{$t('paperlessUrl')} <input bind:value={form.config.connection} placeholder="https://paperless.example" /></label>
      <label>{$t('apiToken')} <input type="password" bind:value={form.config.api_token} placeholder="Paperless API token" /></label>
    {:else if form.type === 'sftp'}
      <div class="grid cols-2">
        <label>{$t('host')} <input bind:value={form.config.host} placeholder="sftp.example.local" /></label>
        <label>{$t('port')} <input type="number" min="1" max="65535" bind:value={form.config.port} /></label>
      </div>
      <div class="grid cols-2">
        <label>{$t('username')} <input bind:value={form.config.username} placeholder="scanner" /></label>
        <label>{$t('password')} <input type="password" bind:value={form.config.password} /></label>
      </div>
      <label>{$t('remotePath')} <input bind:value={form.config.remote_path} placeholder="/inbox/scans" /></label>
    {:else if form.type === 'email'}
      <label>{$t('recipientEmail')} <input bind:value={form.config.connection} placeholder="scan-inbox@example.com" /></label>
      <div class="grid cols-2">
        <label>{$t('smtpHost')} <input bind:value={form.config.smtp_host} placeholder="smtp.example.com" /></label>
        <label>{$t('smtpPort')} <input type="number" min="1" max="65535" bind:value={form.config.smtp_port} /></label>
      </div>
      <div class="grid cols-2">
        <label>{$t('smtpUser')} <input bind:value={form.config.username} /></label>
        <label>{$t('smtpPass')} <input type="password" bind:value={form.config.password} /></label>
      </div>
      <label>{$t('fromAddress')} <input bind:value={form.config.from} placeholder="scan2target@example.com" /></label>
      <label class="checkbox-line"><input type="checkbox" bind:checked={form.config.use_tls} /> {$t('useTls')}</label>
    {:else if form.type === 'nextcloud'}
      <label>{$t('webdavUrl')} <input bind:value={form.config.webdav_url} placeholder="https://nextcloud.example/remote.php/dav/files/user" /></label>
      <div class="grid cols-2">
        <label>{$t('username')} <input bind:value={form.config.username} /></label>
        <label>{$t('password')} <input type="password" bind:value={form.config.password} placeholder="App password" /></label>
      </div>
      <label>{$t('remotePath')} <input bind:value={form.config.remote_path} placeholder="Documents/Scans" /></label>
    {:else}
      <label>{$t('connectionValue')} <input bind:value={form.config.connection} /></label>
    {/if}

    <label class="checkbox-line"><input type="checkbox" bind:checked={form.enabled} /> {$t('enabled')}</label>
    <label class="checkbox-line"><input type="checkbox" bind:checked={form.is_favorite} /> {$t('favorite')}</label>

    <div class="row gap top-gap wrap">
      <button class="btn primary" disabled={!form.name} on:click={() => save(true)}>{$t('testAndSave')}</button>
      <button class="btn ghost" disabled={!form.name} on:click={() => save(false)}>{$t('saveWithoutTest')}</button>
      <button class="btn ghost" on:click={startCreate}>{$t('reset')}</button>
    </div>
  </Card>
</section>
