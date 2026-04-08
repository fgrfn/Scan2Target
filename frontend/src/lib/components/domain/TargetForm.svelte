<script lang="ts">
  import type { Target, TargetIn, TargetType } from '$lib/api/targets';
  import { browseLocalPath, type BrowsePathResult } from '$lib/api/targets';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import Modal from '$lib/components/ui/Modal.svelte';

  interface Props {
    target?: Target | null;
    onSave: (data: TargetIn) => Promise<void>;
    onCancel: () => void;
  }

  let { target = null, onSave, onCancel }: Props = $props();

  const TARGET_TYPES: { value: TargetType; label: string }[] = [
    { value: 'smb', label: 'SMB / Windows Share' },
    { value: 'sftp', label: 'SFTP' },
    { value: 'email', label: 'Email (SMTP)' },
    { value: 'paperless', label: 'Paperless-ngx' },
    { value: 'webhook', label: 'Webhook' },
    { value: 'local', label: 'Local Folder (server)' },
    { value: 'google_drive', label: 'Google Drive' },
    { value: 'dropbox', label: 'Dropbox' },
    { value: 'onedrive', label: 'OneDrive' },
    { value: 'nextcloud', label: 'Nextcloud' }
  ];

  // Form state — initialized from target prop via $effect so re-init works when prop changes
  let name = $state('');
  let type = $state<TargetType>('smb');
  let saving = $state(false);

  // SMB
  let smb_connection = $state('');
  let smb_username = $state('');
  let smb_password = $state('');

  // SFTP
  let sftp_host = $state('');
  let sftp_port = $state('22');
  let sftp_username = $state('');
  let sftp_password = $state('');
  let sftp_path = $state('/');

  // Email
  let email_smtp_host = $state('');
  let email_smtp_port = $state('587');
  let email_username = $state('');
  let email_password = $state('');
  let email_use_tls = $state(true);
  let email_to = $state('');

  // Paperless
  let paperless_connection = $state('');
  let paperless_api_token = $state('');

  // Webhook
  let webhook_connection = $state('');

  // Google Drive
  let gdrive_access_token = $state('');
  let gdrive_folder_id = $state('');

  // Dropbox
  let dropbox_access_token = $state('');
  let dropbox_path = $state('/');

  // OneDrive
  let onedrive_access_token = $state('');
  let onedrive_path = $state('/');

  // Nextcloud
  let nc_webdav_url = $state('');
  let nc_username = $state('');
  let nc_password = $state('');
  let nc_path = $state('/');

  // Local folder
  let local_path = $state('');
  let local_subfolder_per_day = $state(false);
  let showBrowse = $state(false);
  let browseData = $state<BrowsePathResult | null>(null);
  let browseLoading = $state(false);

  // When target prop changes (e.g., switching from edit one target to another), re-populate
  $effect(() => {
    const t = target;
    name = t?.name ?? '';
    type = (t?.type?.toLowerCase() ?? 'smb') as TargetType;

    smb_connection = (t?.config?.connection as string) ?? '';
    smb_username = (t?.config?.username as string) ?? '';
    smb_password = '';

    sftp_host = (t?.config?.host as string) ?? '';
    sftp_port = String((t?.config?.port as number) ?? 22);
    sftp_username = (t?.config?.username as string) ?? '';
    sftp_password = '';
    sftp_path = (t?.config?.path as string) ?? '/';

    email_smtp_host = (t?.config?.smtp_host as string) ?? '';
    email_smtp_port = String((t?.config?.smtp_port as number) ?? 587);
    email_username = (t?.config?.username as string) ?? '';
    email_password = '';
    email_use_tls = Boolean(t?.config?.use_tls ?? true);
    email_to = (t?.config?.to as string) ?? '';

    paperless_connection = (t?.config?.connection as string) ?? '';
    paperless_api_token = (t?.config?.api_token as string) ?? '';

    webhook_connection = (t?.config?.connection as string) ?? '';

    gdrive_access_token = (t?.config?.access_token as string) ?? '';
    gdrive_folder_id = (t?.config?.folder_id as string) ?? '';

    dropbox_access_token = (t?.config?.access_token as string) ?? '';
    dropbox_path = (t?.config?.path as string) ?? '/';

    onedrive_access_token = (t?.config?.access_token as string) ?? '';
    onedrive_path = (t?.config?.path as string) ?? '/';

    nc_webdav_url = (t?.config?.webdav_url as string) ?? '';
    nc_username = (t?.config?.username as string) ?? '';
    nc_password = '';
    nc_path = (t?.config?.path as string) ?? '/';

    local_path = (t?.config?.path as string) ?? '';
    local_subfolder_per_day = Boolean(t?.config?.subfolder_per_day ?? false);
  });

  function buildPayload(): TargetIn {
    let config: Record<string, unknown> = {};

    switch (type) {
      case 'smb':
        config = { connection: smb_connection, username: smb_username, ...(smb_password ? { password: smb_password } : {}) };
        break;
      case 'sftp':
        config = { host: sftp_host, port: Number(sftp_port), path: sftp_path, username: sftp_username, ...(sftp_password ? { password: sftp_password } : {}) };
        break;
      case 'email':
        config = { smtp_host: email_smtp_host, smtp_port: Number(email_smtp_port), use_tls: email_use_tls, to: email_to, username: email_username, ...(email_password ? { password: email_password } : {}) };
        break;
      case 'paperless':
        config = { connection: paperless_connection, api_token: paperless_api_token };
        break;
      case 'webhook':
        config = { connection: webhook_connection };
        break;
      case 'google_drive':
        config = { access_token: gdrive_access_token, folder_id: gdrive_folder_id };
        break;
      case 'dropbox':
        config = { access_token: dropbox_access_token, path: dropbox_path };
        break;
      case 'onedrive':
        config = { access_token: onedrive_access_token, path: onedrive_path };
        break;
      case 'nextcloud':
        config = { webdav_url: nc_webdav_url, path: nc_path, username: nc_username, ...(nc_password ? { password: nc_password } : {}) };
        break;
      case 'local':
        config = { path: local_path, subfolder_per_day: local_subfolder_per_day };
        break;
    }

    return { name, type, config };
  }

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    saving = true;
    try {
      await onSave(buildPayload());
    } finally {
      saving = false;
    }
  }

  async function openBrowse() {
    showBrowse = true;
    await loadBrowse(local_path || undefined);
  }

  async function loadBrowse(path?: string) {
    browseLoading = true;
    try { browseData = await browseLocalPath(path); }
    catch { browseData = null; }
    finally { browseLoading = false; }
  }

  function selectBrowsePath() {
    if (browseData) local_path = browseData.current;
    showBrowse = false;
  }
</script>

<form onsubmit={handleSubmit}>
  <div class="form-group">
    <label class="form-label" for="target-name">Name</label>
    <input
      id="target-name"
      class="form-control"
      type="text"
      bind:value={name}
      required
      placeholder="My Scanner Target"
    />
  </div>

  <div class="form-group">
    <label class="form-label" for="target-type">Type</label>
    <select id="target-type" class="form-control" bind:value={type} disabled={!!target}>
      {#each TARGET_TYPES as t}
        <option value={t.value}>{t.label}</option>
      {/each}
    </select>
    {#if target}
      <p class="form-hint">Type cannot be changed after creation.</p>
    {/if}
  </div>

  <div class="separator"></div>

  <!-- SMB -->
  {#if type === 'smb'}
    <div class="form-group">
      <label class="form-label" for="smb-conn">Share Path</label>
      <input id="smb-conn" class="form-control" type="text" bind:value={smb_connection}
        placeholder="//server/share" required />
      <p class="form-hint">UNC path, e.g. //192.168.1.10/scans</p>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label class="form-label" for="smb-user">Username</label>
        <input id="smb-user" class="form-control" type="text" bind:value={smb_username} placeholder="domain\user" />
      </div>
      <div class="form-group">
        <label class="form-label" for="smb-pass">Password</label>
        <input id="smb-pass" class="form-control" type="password" bind:value={smb_password}
          placeholder={target ? '(unchanged)' : ''} />
      </div>
    </div>
  {/if}

  <!-- SFTP -->
  {#if type === 'sftp'}
    <div class="form-row">
      <div class="form-group">
        <label class="form-label" for="sftp-host">Host</label>
        <input id="sftp-host" class="form-control" type="text" bind:value={sftp_host} placeholder="192.168.1.10" required />
      </div>
      <div class="form-group">
        <label class="form-label" for="sftp-port">Port</label>
        <input id="sftp-port" class="form-control" type="number" bind:value={sftp_port} placeholder="22" min="1" max="65535" />
      </div>
    </div>
    <div class="form-group">
      <label class="form-label" for="sftp-path">Remote Path</label>
      <input id="sftp-path" class="form-control" type="text" bind:value={sftp_path} placeholder="/uploads/scans" />
    </div>
    <div class="form-row">
      <div class="form-group">
        <label class="form-label" for="sftp-user">Username</label>
        <input id="sftp-user" class="form-control" type="text" bind:value={sftp_username} required />
      </div>
      <div class="form-group">
        <label class="form-label" for="sftp-pass">Password</label>
        <input id="sftp-pass" class="form-control" type="password" bind:value={sftp_password}
          placeholder={target ? '(unchanged)' : ''} />
      </div>
    </div>
  {/if}

  <!-- Email -->
  {#if type === 'email'}
    <div class="form-row">
      <div class="form-group">
        <label class="form-label" for="email-host">SMTP Host</label>
        <input id="email-host" class="form-control" type="text" bind:value={email_smtp_host} placeholder="smtp.example.com" required />
      </div>
      <div class="form-group">
        <label class="form-label" for="email-port">SMTP Port</label>
        <input id="email-port" class="form-control" type="number" bind:value={email_smtp_port} placeholder="587" />
      </div>
    </div>
    <div class="form-group">
      <label class="form-label" for="email-to">Recipient Email</label>
      <input id="email-to" class="form-control" type="email" bind:value={email_to} placeholder="user@example.com" required />
    </div>
    <div class="form-row">
      <div class="form-group">
        <label class="form-label" for="email-user">SMTP Username</label>
        <input id="email-user" class="form-control" type="text" bind:value={email_username} />
      </div>
      <div class="form-group">
        <label class="form-label" for="email-pass">SMTP Password</label>
        <input id="email-pass" class="form-control" type="password" bind:value={email_password}
          placeholder={target ? '(unchanged)' : ''} />
      </div>
    </div>
    <div class="form-group">
      <div class="toggle-wrap">
        <label class="toggle" for="email-tls">
          <input id="email-tls" type="checkbox" bind:checked={email_use_tls} />
          <span class="toggle-slider"></span>
        </label>
        <span class="form-label" style="margin-bottom:0">Use TLS/STARTTLS</span>
      </div>
    </div>
  {/if}

  <!-- Paperless -->
  {#if type === 'paperless'}
    <div class="form-group">
      <label class="form-label" for="pl-conn">Paperless URL</label>
      <input id="pl-conn" class="form-control" type="url" bind:value={paperless_connection}
        placeholder="http://paperless:8000" required />
    </div>
    <div class="form-group">
      <label class="form-label" for="pl-token">API Token</label>
      <input id="pl-token" class="form-control" type="password" bind:value={paperless_api_token}
        placeholder={target ? '(unchanged)' : ''} required={!target} />
      <p class="form-hint">Found in Paperless → Profile → API Token</p>
    </div>
  {/if}

  <!-- Webhook -->
  {#if type === 'webhook'}
    <div class="form-group">
      <label class="form-label" for="wh-url">Webhook URL</label>
      <input id="wh-url" class="form-control" type="url" bind:value={webhook_connection}
        placeholder="https://example.com/webhook" required />
      <p class="form-hint">POST with multipart/form-data containing the scanned file.</p>
    </div>
  {/if}

  <!-- Google Drive -->
  {#if type === 'google_drive'}
    <div class="form-group">
      <label class="form-label" for="gdrive-token">Access Token</label>
      <input id="gdrive-token" class="form-control" type="password" bind:value={gdrive_access_token}
        placeholder={target ? '(unchanged)' : ''} />
    </div>
    <div class="form-group">
      <label class="form-label" for="gdrive-folder">Folder ID</label>
      <input id="gdrive-folder" class="form-control" type="text" bind:value={gdrive_folder_id}
        placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs" />
      <p class="form-hint">The folder ID from the Google Drive URL.</p>
    </div>
  {/if}

  <!-- Dropbox -->
  {#if type === 'dropbox'}
    <div class="form-group">
      <label class="form-label" for="db-token">Access Token</label>
      <input id="db-token" class="form-control" type="password" bind:value={dropbox_access_token}
        placeholder={target ? '(unchanged)' : ''} />
    </div>
    <div class="form-group">
      <label class="form-label" for="db-path">Upload Path</label>
      <input id="db-path" class="form-control" type="text" bind:value={dropbox_path} placeholder="/Scans" />
    </div>
  {/if}

  <!-- OneDrive -->
  {#if type === 'onedrive'}
    <div class="form-group">
      <label class="form-label" for="od-token">Access Token</label>
      <input id="od-token" class="form-control" type="password" bind:value={onedrive_access_token}
        placeholder={target ? '(unchanged)' : ''} />
    </div>
    <div class="form-group">
      <label class="form-label" for="od-path">Upload Path</label>
      <input id="od-path" class="form-control" type="text" bind:value={onedrive_path} placeholder="/Documents/Scans" />
    </div>
  {/if}

  <!-- Local Folder -->
  {#if type === 'local'}
    <div class="form-group">
      <label class="form-label" for="lf-path">Folder Path <span style="font-weight:400;color:var(--c-text-3);">(on server)</span></label>
      <div style="display:flex;gap:6px;">
        <input id="lf-path" class="form-control" type="text" bind:value={local_path}
          placeholder="/data/scans" required style="flex:1;" />
        <button type="button" class="btn btn-secondary" onclick={openBrowse} style="white-space:nowrap;flex-shrink:0;">Browse…</button>
      </div>
      <p class="form-hint">Path on the Scan2Target server/container. Defaults to inside <code>/data</code>.</p>
    </div>
    <div class="form-group">
      <div class="toggle-wrap">
        <label class="toggle" for="lf-day">
          <input id="lf-day" type="checkbox" bind:checked={local_subfolder_per_day} />
          <span class="toggle-slider"></span>
        </label>
        <span class="form-label" style="margin-bottom:0">Create dated subfolder (YYYY-MM-DD)</span>
      </div>
    </div>
  {/if}

  <!-- Nextcloud -->
  {#if type === 'nextcloud'}
    <div class="form-group">
      <label class="form-label" for="nc-url">WebDAV URL</label>
      <input id="nc-url" class="form-control" type="url" bind:value={nc_webdav_url}
        placeholder="https://cloud.example.com/remote.php/dav/files/user" required />
    </div>
    <div class="form-group">
      <label class="form-label" for="nc-path">Upload Path</label>
      <input id="nc-path" class="form-control" type="text" bind:value={nc_path} placeholder="/Scans" />
    </div>
    <div class="form-row">
      <div class="form-group">
        <label class="form-label" for="nc-user">Username</label>
        <input id="nc-user" class="form-control" type="text" bind:value={nc_username} required />
      </div>
      <div class="form-group">
        <label class="form-label" for="nc-pass">Password</label>
        <input id="nc-pass" class="form-control" type="password" bind:value={nc_password}
          placeholder={target ? '(unchanged)' : ''} />
      </div>
    </div>
  {/if}

  <div class="form-actions">
    <button type="button" class="btn btn-secondary" onclick={onCancel} disabled={saving}>
      Cancel
    </button>
    <button type="submit" class="btn btn-primary" disabled={saving}>
      {#if saving}<Spinner size="sm" />{/if}
      {target ? 'Save Changes' : 'Create Target'}
    </button>
  </div>
</form>

<!-- Directory Browser Modal -->
<Modal open={showBrowse} title="Choose Folder" onClose={() => (showBrowse = false)}>
  <div style="display:flex;flex-direction:column;gap:10px;min-height:180px;">
    {#if browseLoading}
      <div style="display:flex;align-items:center;gap:8px;padding:16px 0;color:var(--c-text-2);">
        <Spinner /><span>Loading…</span>
      </div>
    {:else if !browseData}
      <p style="color:var(--c-error);font-size:0.875rem;">Could not load directory listing.</p>
    {:else}
      <!-- Breadcrumb / current path -->
      <div style="font-size:0.75rem;font-family:var(--font-mono);color:var(--c-text-2);padding:6px 8px;background:var(--c-surface-2);border:1px solid var(--c-border);border-radius:5px;word-break:break-all;">
        {browseData.current}
      </div>

      <!-- Up button -->
      {#if browseData.parent}
        <button type="button" class="btn btn-secondary btn-sm" style="align-self:flex-start;"
                onclick={() => loadBrowse(browseData!.parent!)}>
          ↑ Up
        </button>
      {/if}

      <!-- Directory listing -->
      {#if !browseData.items.length}
        <p style="font-size:0.8125rem;color:var(--c-text-3);">No subdirectories</p>
      {:else}
        <div style="display:flex;flex-direction:column;gap:4px;max-height:260px;overflow-y:auto;">
          {#each browseData.items as item}
            <button type="button"
                    style="display:flex;align-items:center;gap:8px;padding:7px 10px;border-radius:5px;background:var(--c-surface-2);border:1px solid var(--c-border);color:var(--c-text);font-size:0.875rem;cursor:pointer;text-align:left;width:100%;"
                    onclick={() => loadBrowse(item.path)}>
              <span style="color:var(--c-text-3);">📁</span>
              {item.name}
            </button>
          {/each}
        </div>
      {/if}
    {/if}
  </div>

  {#if browseData}
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px;padding-top:12px;border-top:1px solid var(--c-border);">
      <button type="button" class="btn btn-secondary" onclick={() => (showBrowse = false)}>Cancel</button>
      <button type="button" class="btn btn-primary" onclick={selectBrowsePath}>
        Select "{browseData.current.split('/').at(-1) || '/'}"
      </button>
    </div>
  {/if}
</Modal>

<style>
  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding-top: 8px;
    margin-top: 8px;
    border-top: 1px solid var(--c-border);
  }
</style>
