<script lang="ts">
  import { onMount } from 'svelte';
  import { auth } from '$lib/stores/auth.svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import { getSettings, updateSetting, type AppSettings } from '$lib/api/settings';
  import { runCleanup, getDiskUsage, type DiskUsage } from '$lib/api/maintenance';
  import Spinner from '$lib/components/ui/Spinner.svelte';

  let settings = $state<AppSettings | null>(null);
  let loading = $state(true);
  let savingKey = $state<string | null>(null);

  // Local editable copies
  let requireAuth = $state(false);
  let logLevel = $state('INFO');
  let healthCheckInterval = $state(30);
  let scannerCheckInterval = $state(60);
  let commandTimeout = $state(120);
  let corsOrigins = $state('[]');

  let diskUsage = $state<DiskUsage | null>(null);
  let loadingDisk = $state(false);
  let cleaningUp = $state(false);

  const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];

  onMount(async () => {
    await Promise.all([loadSettings(), loadDiskUsage()]);
  });

  async function loadSettings() {
    loading = true;
    try {
      const s = await getSettings();
      settings = s;
      requireAuth = s.require_auth;
      logLevel = s.log_level;
      healthCheckInterval = s.health_check_interval;
      scannerCheckInterval = s.scanner_check_interval;
      commandTimeout = s.command_timeout;
      corsOrigins = JSON.stringify(s.cors_origins, null, 2);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load settings', 'error');
    } finally {
      loading = false;
    }
  }

  async function loadDiskUsage() {
    loadingDisk = true;
    try {
      diskUsage = await getDiskUsage();
    } catch {
      // non-critical
    } finally {
      loadingDisk = false;
    }
  }

  async function save(key: string, value: unknown) {
    savingKey = key;
    try {
      await updateSetting(key, value);
      showToast(`Setting "${key}" saved`, 'success');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Save failed', 'error');
    } finally {
      savingKey = null;
    }
  }

  async function saveRequireAuth() {
    await save('require_auth', requireAuth);
  }

  async function saveLogLevel() {
    await save('log_level', logLevel);
  }

  async function saveHealthCheckInterval() {
    await save('health_check_interval', healthCheckInterval);
  }

  async function saveScannerCheckInterval() {
    await save('scanner_check_interval', scannerCheckInterval);
  }

  async function saveCommandTimeout() {
    await save('command_timeout', commandTimeout);
  }

  async function saveCorsOrigins() {
    let parsed: unknown;
    try {
      parsed = JSON.parse(corsOrigins);
    } catch {
      showToast('Invalid JSON for CORS origins', 'error');
      return;
    }
    await save('cors_origins', parsed);
  }

  async function handleCleanup() {
    if (!confirm('Run maintenance cleanup? This will delete temporary scan files.')) return;
    cleaningUp = true;
    try {
      const result = await runCleanup();
      showToast(`Cleanup done: ${result.deleted_files} files, ${formatBytes(result.freed_bytes)} freed`, 'success');
      await loadDiskUsage();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Cleanup failed', 'error');
    } finally {
      cleaningUp = false;
    }
  }

  function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
  }

  function diskPct(usage: DiskUsage): number {
    if (usage.total_bytes === 0) return 0;
    return (usage.used_bytes / usage.total_bytes) * 100;
  }

  const isAdmin = $derived(auth.user?.is_admin ?? false);
</script>

<div class="page-header">
  <h1 class="page-title">⚙ Settings</h1>
  <p class="page-subtitle">Application configuration and maintenance</p>
</div>

<div class="page-body">
  {#if !isAdmin}
    <div class="card">
      <div class="empty-state">
        <div class="empty-icon">🔒</div>
        <p>Settings are only accessible to administrators.</p>
      </div>
    </div>
  {:else if loading}
    <div class="flex items-center gap-3">
      <Spinner />
      <span class="text-muted">Loading…</span>
    </div>
  {:else}
    <div class="settings-layout">
      <!-- Auth settings -->
      <div class="card">
        <h2 class="card-title">🔐 Authentication</h2>
        <div class="setting-row">
          <div class="setting-info">
            <label class="setting-label" for="req-auth">Require Authentication</label>
            <p class="form-hint">When disabled, the app is accessible without login.</p>
          </div>
          <div class="setting-control">
            <label class="toggle" for="req-auth">
              <input id="req-auth" type="checkbox" bind:checked={requireAuth} />
              <span class="toggle-slider"></span>
            </label>
            <button
              class="btn btn-primary btn-sm"
              onclick={saveRequireAuth}
              disabled={savingKey === 'require_auth'}
            >
              {#if savingKey === 'require_auth'}<Spinner size="sm" />{/if}
              Save
            </button>
          </div>
        </div>
      </div>

      <!-- Logging -->
      <div class="card">
        <h2 class="card-title">📝 Logging</h2>
        <div class="setting-row">
          <div class="setting-info">
            <label class="setting-label" for="log-level">Log Level</label>
            <p class="form-hint">Verbosity of application logs.</p>
          </div>
          <div class="setting-control">
            <select id="log-level" class="form-control" style="width:auto" bind:value={logLevel}>
              {#each LOG_LEVELS as level}
                <option value={level}>{level}</option>
              {/each}
            </select>
            <button
              class="btn btn-primary btn-sm"
              onclick={saveLogLevel}
              disabled={savingKey === 'log_level'}
            >
              {#if savingKey === 'log_level'}<Spinner size="sm" />{/if}
              Save
            </button>
          </div>
        </div>
      </div>

      <!-- Intervals -->
      <div class="card">
        <h2 class="card-title">⏱ Intervals</h2>
        <div class="setting-row">
          <div class="setting-info">
            <label class="setting-label" for="health-interval">Health Check Interval</label>
            <p class="form-hint">How often to check device health (seconds).</p>
          </div>
          <div class="setting-control">
            <input
              id="health-interval"
              class="form-control"
              type="number"
              min="5"
              max="3600"
              bind:value={healthCheckInterval}
              style="width:90px"
            />
            <button
              class="btn btn-primary btn-sm"
              onclick={saveHealthCheckInterval}
              disabled={savingKey === 'health_check_interval'}
            >
              {#if savingKey === 'health_check_interval'}<Spinner size="sm" />{/if}
              Save
            </button>
          </div>
        </div>

        <div class="separator"></div>

        <div class="setting-row">
          <div class="setting-info">
            <label class="setting-label" for="scanner-interval">Scanner Check Interval</label>
            <p class="form-hint">How often to check scanner availability (seconds).</p>
          </div>
          <div class="setting-control">
            <input
              id="scanner-interval"
              class="form-control"
              type="number"
              min="5"
              max="3600"
              bind:value={scannerCheckInterval}
              style="width:90px"
            />
            <button
              class="btn btn-primary btn-sm"
              onclick={saveScannerCheckInterval}
              disabled={savingKey === 'scanner_check_interval'}
            >
              {#if savingKey === 'scanner_check_interval'}<Spinner size="sm" />{/if}
              Save
            </button>
          </div>
        </div>

        <div class="separator"></div>

        <div class="setting-row">
          <div class="setting-info">
            <label class="setting-label" for="cmd-timeout">Command Timeout</label>
            <p class="form-hint">Max time for scan commands before aborting (seconds).</p>
          </div>
          <div class="setting-control">
            <input
              id="cmd-timeout"
              class="form-control"
              type="number"
              min="10"
              max="600"
              bind:value={commandTimeout}
              style="width:90px"
            />
            <button
              class="btn btn-primary btn-sm"
              onclick={saveCommandTimeout}
              disabled={savingKey === 'command_timeout'}
            >
              {#if savingKey === 'command_timeout'}<Spinner size="sm" />{/if}
              Save
            </button>
          </div>
        </div>
      </div>

      <!-- CORS -->
      <div class="card">
        <h2 class="card-title">🌐 CORS Origins</h2>
        <div class="form-group">
          <label class="form-label" for="cors-origins">Allowed Origins (JSON array)</label>
          <textarea
            id="cors-origins"
            class="form-control font-mono"
            rows="4"
            bind:value={corsOrigins}
          ></textarea>
          <p class="form-hint">JSON array of allowed origins, e.g. ["https://app.example.com"]</p>
        </div>
        <button
          class="btn btn-primary btn-sm"
          onclick={saveCorsOrigins}
          disabled={savingKey === 'cors_origins'}
        >
          {#if savingKey === 'cors_origins'}<Spinner size="sm" />{/if}
          Save CORS Origins
        </button>
      </div>

      <!-- Maintenance -->
      <div class="card">
        <h2 class="card-title">🛠 Maintenance</h2>

        {#if diskUsage}
          <div class="disk-info mb-4">
            <div class="flex justify-between" style="margin-bottom:6px;font-size:0.875rem">
              <span class="text-muted">Disk Usage</span>
              <span>{formatBytes(diskUsage.used_bytes)} / {formatBytes(diskUsage.total_bytes)}</span>
            </div>
            <div class="disk-bar-track">
              <div class="disk-bar-fill" style="width:{diskPct(diskUsage).toFixed(1)}%"></div>
            </div>
            <div class="flex justify-between" style="margin-top:6px;font-size:0.78rem;color:var(--color-text-dim)">
              <span>Scan files: {formatBytes(diskUsage.scan_dir_bytes)}</span>
              <span>{diskPct(diskUsage).toFixed(1)}% used</span>
            </div>
          </div>
        {:else if loadingDisk}
          <div class="flex items-center gap-2 mb-4">
            <Spinner size="sm" />
            <span class="text-muted" style="font-size:0.875rem">Loading disk info…</span>
          </div>
        {/if}

        <div class="flex gap-3 flex-wrap">
          <button
            class="btn btn-secondary"
            onclick={handleCleanup}
            disabled={cleaningUp}
          >
            {#if cleaningUp}<Spinner size="sm" />{/if}
            Run Cleanup
          </button>
          <button
            class="btn btn-ghost btn-sm"
            onclick={loadDiskUsage}
            disabled={loadingDisk}
          >
            {#if loadingDisk}<Spinner size="sm" />{/if}
            Refresh Disk Info
          </button>
        </div>
        <p class="form-hint" style="margin-top:10px">
          Cleanup removes temporary and orphaned scan files older than the retention period.
        </p>
      </div>
    </div>
  {/if}
</div>

<style>
  .settings-layout {
    display: flex;
    flex-direction: column;
    gap: 20px;
    max-width: 680px;
  }

  .setting-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }

  .setting-info {
    flex: 1;
    min-width: 180px;
  }

  .setting-label {
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--color-text);
    display: block;
    margin-bottom: 4px;
  }

  .setting-control {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }

  .disk-bar-track {
    height: 8px;
    background: var(--color-surface-raised);
    border-radius: var(--radius-full);
    overflow: hidden;
  }

  .disk-bar-fill {
    height: 100%;
    background: var(--color-primary);
    border-radius: var(--radius-full);
    transition: width 0.4s ease;
  }
</style>
