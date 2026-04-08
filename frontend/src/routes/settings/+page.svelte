<script lang="ts">
  import { onMount } from 'svelte';
  import { auth } from '$lib/stores/auth.svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import { getSettings, updateSetting, type AppSettings } from '$lib/api/settings';
  import { runCleanup, getDiskUsage, type DiskUsage } from '$lib/api/maintenance';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import { Shield, Terminal, Timer, Globe, HardDrive, RefreshCw, Trash2, Loader2, Lock, Save } from 'lucide-svelte';

  let loading = $state(true); let savingKey = $state<string|null>(null);
  let requireAuth = $state(false); let logLevel = $state('INFO');
  let healthCheckInterval = $state(30); let scannerCheckInterval = $state(60); let commandTimeout = $state(120);
  let corsOrigins = $state('[]');
  let diskUsage = $state<DiskUsage|null>(null); let loadingDisk = $state(false); let cleaningUp = $state(false);

  const LOG_LEVELS = ['DEBUG','INFO','WARNING','ERROR','CRITICAL'];
  const isAdmin = $derived(auth.user?.is_admin??false);

  onMount(()=>Promise.all([loadSettings(),loadDisk()]));

  async function loadSettings(){ loading=true; try{ const s=await getSettings(); requireAuth=s.require_auth;logLevel=s.log_level;healthCheckInterval=s.health_check_interval;scannerCheckInterval=s.scanner_check_interval;commandTimeout=s.command_timeout;corsOrigins=JSON.stringify(s.cors_origins,null,2); }catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}finally{loading=false;} }

  async function loadDisk(){ loadingDisk=true; try{diskUsage=await getDiskUsage();}catch{} finally{loadingDisk=false;} }

  async function save(key:string,value:unknown){ savingKey=key; try{await updateSetting(key,value);showToast('Saved','success');}catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}finally{savingKey=null;} }

  async function saveCors(){
    let p:unknown;
    try{ p=JSON.parse(corsOrigins); }catch{ showToast('Invalid JSON','error'); return; }
    if(!Array.isArray(p)||p.some(v=>typeof v!=='string')){ showToast('Must be a JSON array of strings','error'); return; }
    await save('cors_origins',p);
  }

  async function handleCleanup(){ if(!confirm('Run cleanup? Temporary scan files will be deleted.'))return; cleaningUp=true; try{const r=await runCleanup();showToast(`Done: ${r.deleted_files + r.deleted_thumbnails} files deleted`,'success');await loadDisk();}catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}finally{cleaningUp=false;} }

  function fmtB(b:number){ if(b<1024)return`${b} B`; if(b<1048576)return`${(b/1024).toFixed(1)} KB`; if(b<1073741824)return`${(b/1048576).toFixed(1)} MB`; return`${(b/1073741824).toFixed(2)} GB`; }
  function diskBarColor(p:number){ return p>85?'var(--c-err)':p>60?'var(--c-warn)':'var(--c-accent)'; }
</script>

<div class="page-wrap">
  <div style="margin-bottom:20px;">
    <h1 class="page-title">Settings</h1>
    <p class="page-sub">Application configuration and maintenance</p>
  </div>

  {#if !isAdmin}
    <div class="card"><div class="empty-state"><Lock size={28} style="color:var(--c-surface-3);" /><p>Settings are only accessible to administrators.</p></div></div>
  {:else if loading}
    <div style="display:flex;align-items:center;gap:10px;color:var(--c-text-2);padding:48px 0;"><Spinner /><span>Loading…</span></div>
  {:else}
    <div style="display:flex;flex-direction:column;gap:12px;max-width:640px;">

      <!-- Authentication -->
      <div class="card">
        <div class="card-header"><span class="card-title"><Shield size={13} />Authentication</span></div>
        <div class="card-body">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;">
            <div style="flex:1;">
              <p style="font-size:0.875rem;font-weight:500;color:var(--c-text);">Require Authentication</p>
              <p class="form-hint">When disabled, the app is publicly accessible.</p>
            </div>
            <div style="display:flex;align-items:center;gap:10px;flex-shrink:0;">
              <label class="toggle" for="ra"><input id="ra" type="checkbox" bind:checked={requireAuth} /><span class="toggle-slider"></span></label>
              <button class="btn btn-primary btn-sm" onclick={()=>save('require_auth',requireAuth)} disabled={savingKey==='require_auth'}>
                {#if savingKey==='require_auth'}<Loader2 size={12} class="spin" />{:else}<Save size={12} />{/if}Save
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Logging -->
      <div class="card">
        <div class="card-header"><span class="card-title"><Terminal size={13} />Logging</span></div>
        <div class="card-body">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;">
            <div style="flex:1;">
              <label style="font-size:0.875rem;font-weight:500;color:var(--c-text);display:block;" for="ll">Log Level</label>
              <p class="form-hint">Verbosity of application logs.</p>
            </div>
            <div style="display:flex;align-items:center;gap:10px;flex-shrink:0;">
              <select id="ll" class="form-control" style="width:auto;" bind:value={logLevel}>
                {#each LOG_LEVELS as l}<option value={l}>{l}</option>{/each}
              </select>
              <button class="btn btn-primary btn-sm" onclick={()=>save('log_level',logLevel)} disabled={savingKey==='log_level'}>
                {#if savingKey==='log_level'}<Loader2 size={12} class="spin" />{:else}<Save size={12} />{/if}Save
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Intervals -->
      <div class="card">
        <div class="card-header"><span class="card-title"><Timer size={13} />Intervals</span></div>
        <div class="card-body" style="display:flex;flex-direction:column;gap:16px;">

          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;">
            <div style="flex:1;min-width:160px;">
              <label style="font-size:0.875rem;font-weight:500;color:var(--c-text);display:block;" for="hci">Health Check Interval</label>
              <p class="form-hint">How often to check device health (seconds).</p>
            </div>
            <div style="display:flex;align-items:center;gap:10px;flex-shrink:0;">
              <input id="hci" class="form-control" type="number" min="5" max="3600" style="width:84px;" bind:value={healthCheckInterval} />
              <button class="btn btn-primary btn-sm" onclick={()=>save('health_check_interval',healthCheckInterval)} disabled={savingKey==='health_check_interval'}>
                {#if savingKey==='health_check_interval'}<Loader2 size={12} class="spin" />{:else}<Save size={12} />{/if}Save
              </button>
            </div>
          </div>

          <hr style="border-color:var(--c-border);margin:0;" />

          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;">
            <div style="flex:1;min-width:160px;">
              <label style="font-size:0.875rem;font-weight:500;color:var(--c-text);display:block;" for="sci">Scanner Check Interval</label>
              <p class="form-hint">How often to check scanner availability (seconds).</p>
            </div>
            <div style="display:flex;align-items:center;gap:10px;flex-shrink:0;">
              <input id="sci" class="form-control" type="number" min="5" max="3600" style="width:84px;" bind:value={scannerCheckInterval} />
              <button class="btn btn-primary btn-sm" onclick={()=>save('scanner_check_interval',scannerCheckInterval)} disabled={savingKey==='scanner_check_interval'}>
                {#if savingKey==='scanner_check_interval'}<Loader2 size={12} class="spin" />{:else}<Save size={12} />{/if}Save
              </button>
            </div>
          </div>

          <hr style="border-color:var(--c-border);margin:0;" />

          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;">
            <div style="flex:1;min-width:160px;">
              <label style="font-size:0.875rem;font-weight:500;color:var(--c-text);display:block;" for="cto">Command Timeout</label>
              <p class="form-hint">Max time for scan commands before aborting (seconds).</p>
            </div>
            <div style="display:flex;align-items:center;gap:10px;flex-shrink:0;">
              <input id="cto" class="form-control" type="number" min="10" max="600" style="width:84px;" bind:value={commandTimeout} />
              <button class="btn btn-primary btn-sm" onclick={()=>save('command_timeout',commandTimeout)} disabled={savingKey==='command_timeout'}>
                {#if savingKey==='command_timeout'}<Loader2 size={12} class="spin" />{:else}<Save size={12} />{/if}Save
              </button>
            </div>
          </div>

        </div>
      </div>

      <!-- CORS -->
      <div class="card">
        <div class="card-header"><span class="card-title"><Globe size={13} />CORS Origins</span></div>
        <div class="card-body" style="display:flex;flex-direction:column;gap:12px;">
          <div class="form-group">
            <label class="form-label" for="co">Allowed Origins (JSON array)</label>
            <textarea id="co" class="form-control font-mono" rows="4" bind:value={corsOrigins}></textarea>
            <span class="form-hint">e.g. <code style="color:var(--c-text-2);">["https://app.example.com"]</code></span>
          </div>
          <button class="btn btn-primary btn-sm" style="width:fit-content;" onclick={saveCors} disabled={savingKey==='cors_origins'}>
            {#if savingKey==='cors_origins'}<Loader2 size={12} class="spin" />{:else}<Save size={12} />{/if}Save CORS
          </button>
        </div>
      </div>

      <!-- Maintenance -->
      <div class="card">
        <div class="card-header"><span class="card-title"><HardDrive size={13} />Maintenance</span></div>
        <div class="card-body" style="display:flex;flex-direction:column;gap:14px;">
          {#if diskUsage}
            <div>
              <div style="display:flex;justify-content:space-between;margin-bottom:6px;font-size:0.8125rem;">
                <span style="color:var(--c-text-2);">Disk Usage</span>
                <span style="color:var(--c-text);">{fmtB(diskUsage.used_bytes)} / {fmtB(diskUsage.total_bytes)}</span>
              </div>
              <div class="progress-track" style="height:5px;">
                <div class="progress-fill" style="width:{diskPct(diskUsage).toFixed(1)}%;background:{diskBarColor(diskPct(diskUsage))};"></div>
              </div>
              <div style="display:flex;justify-content:space-between;margin-top:5px;font-size:0.6875rem;color:var(--c-text-3);">
                <span>Scan files: {fmtB(diskUsage.scan_dir_bytes)}</span>
                <span>{diskPct(diskUsage).toFixed(1)}% used</span>
              </div>
            </div>
          {:else if loadingDisk}
            <div style="display:flex;align-items:center;gap:8px;font-size:0.8125rem;color:var(--c-text-2);"><Loader2 size={13} class="spin" />Loading disk info…</div>
          {/if}

          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <button class="btn btn-secondary" onclick={handleCleanup} disabled={cleaningUp}>
              {#if cleaningUp}<Loader2 size={14} class="spin" />{:else}<Trash2 size={14} />{/if}Run Cleanup
            </button>
            <button class="btn btn-ghost btn-sm" onclick={loadDisk} disabled={loadingDisk}>
              {#if loadingDisk}<Loader2 size={13} class="spin" />{:else}<RefreshCw size={13} />{/if}Refresh
            </button>
          </div>
          <p class="form-hint">Removes temporary and orphaned scan files older than the retention period.</p>
        </div>
      </div>

    </div>
  {/if}
</div>

<style>
  :global(.spin){animation:spin .7s linear infinite;}
  @keyframes spin{to{transform:rotate(360deg);}}
</style>
