<script lang="ts">
  import { onMount } from 'svelte';
  import { auth } from '$lib/stores/auth.svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import { getSettings, updateSetting, type AppSettings } from '$lib/api/settings';
  import { runCleanup, getDiskUsage, type DiskUsage } from '$lib/api/maintenance';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import { Shield, Terminal, Timer, Globe, HardDrive, RefreshCw, Trash2,
           Loader2, Lock, Save } from 'lucide-svelte';

  let settings             = $state<AppSettings | null>(null);
  let loading              = $state(true);
  let savingKey            = $state<string | null>(null);
  let requireAuth          = $state(false);
  let logLevel             = $state('INFO');
  let healthCheckInterval  = $state(30);
  let scannerCheckInterval = $state(60);
  let commandTimeout       = $state(120);
  let corsOrigins          = $state('[]');
  let diskUsage            = $state<DiskUsage | null>(null);
  let loadingDisk          = $state(false);
  let cleaningUp           = $state(false);

  const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
  const isAdmin = $derived(auth.user?.is_admin ?? false);

  onMount(() => Promise.all([loadSettings(), loadDiskUsage()]));

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
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Failed', 'error'); }
    finally { loading = false; }
  }

  async function loadDiskUsage() {
    loadingDisk = true;
    try { diskUsage = await getDiskUsage(); } catch { /* non-critical */ }
    finally { loadingDisk = false; }
  }

  async function save(key: string, value: unknown) {
    savingKey = key;
    try { await updateSetting(key, value); showToast(`Saved`, 'success'); }
    catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Save failed', 'error'); }
    finally { savingKey = null; }
  }

  async function saveCorsOrigins() {
    let parsed: unknown;
    try { parsed = JSON.parse(corsOrigins); }
    catch { showToast('Invalid JSON for CORS origins', 'error'); return; }
    await save('cors_origins', parsed);
  }

  async function handleCleanup() {
    if (!confirm('Run maintenance cleanup? This will delete temporary scan files.')) return;
    cleaningUp = true;
    try {
      const result = await runCleanup();
      showToast(`Cleanup done: ${result.deleted_files} files, ${fmtBytes(result.freed_bytes)} freed`, 'success');
      await loadDiskUsage();
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Cleanup failed', 'error'); }
    finally { cleaningUp = false; }
  }

  function fmtBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes/1024).toFixed(1)} KB`;
    if (bytes < 1073741824) return `${(bytes/1048576).toFixed(1)} MB`;
    return `${(bytes/1073741824).toFixed(2)} GB`;
  }

  function diskPct(u: DiskUsage) { return u.total_bytes === 0 ? 0 : (u.used_bytes/u.total_bytes)*100; }
</script>

<div class="page-wrap">
  <div class="mb-6">
    <h1 class="page-title">Settings</h1>
    <p class="page-sub">Application configuration and maintenance</p>
  </div>

  {#if !isAdmin}
    <div class="card">
      <div class="empty-state">
        <Lock size={40} class="text-zinc-800" />
        <p>Settings are only accessible to administrators.</p>
      </div>
    </div>
  {:else if loading}
    <div class="flex items-center gap-3 text-zinc-500 py-12"><Spinner /><span>Loading…</span></div>
  {:else}
    <div class="flex flex-col gap-4 max-w-2xl">

      <!-- Authentication -->
      <div class="card">
        <div class="card-header">
          <span class="card-title flex items-center gap-2"><Shield size={14} class="text-indigo-400" /> Authentication</span>
        </div>
        <div class="card-body">
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1">
              <p class="text-sm font-medium text-zinc-200">Require Authentication</p>
              <p class="form-hint">When disabled, the app is accessible without login.</p>
            </div>
            <div class="flex items-center gap-3 flex-shrink-0">
              <label class="toggle" for="req-auth">
                <input id="req-auth" type="checkbox" bind:checked={requireAuth} />
                <span class="toggle-slider"></span>
              </label>
              <button class="btn btn-primary btn-sm" onclick={() => save('require_auth', requireAuth)}
                      disabled={savingKey === 'require_auth'}>
                {#if savingKey === 'require_auth'}<Loader2 size={12} class="animate-spin" />{:else}<Save size={12} />{/if}
                Save
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Logging -->
      <div class="card">
        <div class="card-header">
          <span class="card-title flex items-center gap-2"><Terminal size={14} class="text-indigo-400" /> Logging</span>
        </div>
        <div class="card-body">
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1">
              <label class="text-sm font-medium text-zinc-200 block" for="log-level">Log Level</label>
              <p class="form-hint">Verbosity of application logs.</p>
            </div>
            <div class="flex items-center gap-3 flex-shrink-0">
              <select id="log-level" class="form-control" style="width:auto;" bind:value={logLevel}>
                {#each LOG_LEVELS as level}<option value={level}>{level}</option>{/each}
              </select>
              <button class="btn btn-primary btn-sm" onclick={() => save('log_level', logLevel)}
                      disabled={savingKey === 'log_level'}>
                {#if savingKey === 'log_level'}<Loader2 size={12} class="animate-spin" />{:else}<Save size={12} />{/if}
                Save
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Intervals -->
      <div class="card">
        <div class="card-header">
          <span class="card-title flex items-center gap-2"><Timer size={14} class="text-indigo-400" /> Intervals</span>
        </div>
        <div class="card-body flex flex-col gap-4">

          <!-- Health check -->
          <div class="flex items-start justify-between gap-4 flex-wrap">
            <div class="flex-1 min-w-40">
              <label class="text-sm font-medium text-zinc-200 block" for="hci">Health Check Interval</label>
              <p class="form-hint">How often to check device health (seconds).</p>
            </div>
            <div class="flex items-center gap-3 flex-shrink-0">
              <input id="hci" class="form-control" type="number" min="5" max="3600"
                     bind:value={healthCheckInterval} style="width:90px;" />
              <button class="btn btn-primary btn-sm" onclick={() => save('health_check_interval', healthCheckInterval)}
                      disabled={savingKey === 'health_check_interval'}>
                {#if savingKey === 'health_check_interval'}<Loader2 size={12} class="animate-spin" />{:else}<Save size={12} />{/if}
                Save
              </button>
            </div>
          </div>

          <hr class="border-zinc-800" />

          <!-- Scanner check -->
          <div class="flex items-start justify-between gap-4 flex-wrap">
            <div class="flex-1 min-w-40">
              <label class="text-sm font-medium text-zinc-200 block" for="sci">Scanner Check Interval</label>
              <p class="form-hint">How often to check scanner availability (seconds).</p>
            </div>
            <div class="flex items-center gap-3 flex-shrink-0">
              <input id="sci" class="form-control" type="number" min="5" max="3600"
                     bind:value={scannerCheckInterval} style="width:90px;" />
              <button class="btn btn-primary btn-sm" onclick={() => save('scanner_check_interval', scannerCheckInterval)}
                      disabled={savingKey === 'scanner_check_interval'}>
                {#if savingKey === 'scanner_check_interval'}<Loader2 size={12} class="animate-spin" />{:else}<Save size={12} />{/if}
                Save
              </button>
            </div>
          </div>

          <hr class="border-zinc-800" />

          <!-- Command timeout -->
          <div class="flex items-start justify-between gap-4 flex-wrap">
            <div class="flex-1 min-w-40">
              <label class="text-sm font-medium text-zinc-200 block" for="cto">Command Timeout</label>
              <p class="form-hint">Max time for scan commands (seconds).</p>
            </div>
            <div class="flex items-center gap-3 flex-shrink-0">
              <input id="cto" class="form-control" type="number" min="10" max="600"
                     bind:value={commandTimeout} style="width:90px;" />
              <button class="btn btn-primary btn-sm" onclick={() => save('command_timeout', commandTimeout)}
                      disabled={savingKey === 'command_timeout'}>
                {#if savingKey === 'command_timeout'}<Loader2 size={12} class="animate-spin" />{:else}<Save size={12} />{/if}
                Save
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- CORS -->
      <div class="card">
        <div class="card-header">
          <span class="card-title flex items-center gap-2"><Globe size={14} class="text-indigo-400" /> CORS Origins</span>
        </div>
        <div class="card-body flex flex-col gap-3">
          <div class="form-group">
            <label class="form-label" for="cors-origins">Allowed Origins (JSON array)</label>
            <textarea id="cors-origins" class="form-control font-mono" rows="4"
                      bind:value={corsOrigins}></textarea>
            <span class="form-hint">e.g. <code class="text-zinc-400">["https://app.example.com"]</code></span>
          </div>
          <button class="btn btn-primary btn-sm self-start" onclick={saveCorsOrigins}
                  disabled={savingKey === 'cors_origins'}>
            {#if savingKey === 'cors_origins'}<Loader2 size={12} class="animate-spin" />{:else}<Save size={12} />{/if}
            Save CORS Origins
          </button>
        </div>
      </div>

      <!-- Maintenance -->
      <div class="card">
        <div class="card-header">
          <span class="card-title flex items-center gap-2"><HardDrive size={14} class="text-indigo-400" /> Maintenance</span>
        </div>
        <div class="card-body flex flex-col gap-4">

          {#if diskUsage}
            <div>
              <div class="flex justify-between text-sm mb-1.5">
                <span class="text-zinc-400">Disk Usage</span>
                <span class="text-zinc-300">{fmtBytes(diskUsage.used_bytes)} / {fmtBytes(diskUsage.total_bytes)}</span>
              </div>
              <div class="progress-track">
                <div class="progress-fill"
                     style="width:{diskPct(diskUsage).toFixed(1)}%;
                            background:{diskPct(diskUsage)>85?'#f87171':diskPct(diskUsage)>60?'#fbbf24':'#6366f1'};">
                </div>
              </div>
              <div class="flex justify-between mt-1" style="font-size:0.75rem;color:#52525b;">
                <span>Scan files: {fmtBytes(diskUsage.scan_dir_bytes)}</span>
                <span>{diskPct(diskUsage).toFixed(1)}% used</span>
              </div>
            </div>
          {:else if loadingDisk}
            <div class="flex items-center gap-2 text-zinc-500 text-sm">
              <Loader2 size={14} class="animate-spin" /> Loading disk info…
            </div>
          {/if}

          <div class="flex gap-3 flex-wrap">
            <button class="btn btn-secondary" onclick={handleCleanup} disabled={cleaningUp}>
              {#if cleaningUp}<Loader2 size={14} class="animate-spin" />{:else}<Trash2 size={14} />{/if}
              Run Cleanup
            </button>
            <button class="btn btn-ghost btn-sm" onclick={loadDiskUsage} disabled={loadingDisk}>
              {#if loadingDisk}<Loader2 size={13} class="animate-spin" />{:else}<RefreshCw size={13} />{/if}
              Refresh Disk Info
            </button>
          </div>
          <p class="form-hint">Cleanup removes temporary and orphaned scan files older than the retention period.</p>
        </div>
      </div>

    </div>
  {/if}
</div>

<style>
  :global(.animate-spin) { animation: spin 0.75s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
