<script lang="ts">
  import { onMount } from 'svelte';
  import { wsStore } from '$lib/stores/ws.svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import { listDevices, type Device } from '$lib/api/devices';
  import { listTargets, type Target } from '$lib/api/targets';
  import { getProfiles, startScan, listJobs, cancelJob, previewScan, startBatch, getJob, type ScanProfile, type Job } from '$lib/api/scan';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import { ScanLine, Upload, Eye, Plus, X, CheckCircle2, XCircle, Loader2, Clock, Layers, ChevronRight } from 'lucide-svelte';

  let devices = $state<Device[]>([]); let targets = $state<Target[]>([]);
  let profiles = $state<ScanProfile[]>([]); let recentJobs = $state<Job[]>([]);
  let loading = $state(true); let scanning = $state(false);
  let previewing = $state(false); let previewImage = $state<string | null>(null);
  let activeJob = $state<Job | null>(null);
  let selectedDeviceId  = $state<string | null>(null);
  let selectedTargetId  = $state<string | null>(null);
  let selectedProfileId = $state<string>('');
  let filenamePrefix    = $state('scan');
  let webhookUrl        = $state('');
  let batchMode         = $state(false);
  let batchPages        = $state<string[]>([]);
  let batchPagePreviews = $state<string[]>([]);
  let batchScanning     = $state(false);
  let batchFinishing    = $state(false);

  const sd = $derived([...devices].sort((a,b) => Number(b.is_favorite)-Number(a.is_favorite)));
  const st = $derived([...targets].sort((a,b) => Number(b.is_favorite)-Number(a.is_favorite)));

  onMount(async () => {
    try {
      const [d,t,p,j] = await Promise.all([listDevices(),listTargets(),getProfiles(),listJobs()]);
      devices=d; targets=t; profiles=p; recentJobs=j.slice(0,6);
      if(sd.length) selectedDeviceId=sd[0].id;
      if(st.length) selectedTargetId=st[0].id;
      if(p.length)  selectedProfileId=p[0].id;
    } catch(err: unknown) { showToast(err instanceof Error ? err.message : 'Failed','error'); }
    finally { loading=false; }
  });

  $effect(() => {
    const u = wsStore.lastJobUpdate; if(!u) return;
    if(activeJob && u.id===activeJob.id) activeJob=u;
    recentJobs = recentJobs.map(j => j.id===u.id ? u : j);
  });

  async function handleScan() {
    if(!selectedDeviceId||!selectedTargetId||!selectedProfileId){ showToast('Select device, target & profile','error'); return; }
    scanning=true; previewImage=null; activeJob=null;
    try {
      const resp = await startScan({device_id:selectedDeviceId,profile_id:selectedProfileId,target_id:selectedTargetId,filename_prefix:filenamePrefix,webhook_url:webhookUrl||undefined});
      const job = await getJob(resp.job_id);
      activeJob=job; recentJobs=[job,...recentJobs].slice(0,6); showToast('Scan started','success');
    } catch(err: unknown){ showToast(err instanceof Error ? err.message : 'Failed','error'); }
    finally { scanning=false; }
  }

  async function handlePreview() {
    if(!selectedDeviceId||!selectedProfileId){ showToast('Select device & profile','error'); return; }
    previewing=true; previewImage=null;
    try { const r=await previewScan(selectedDeviceId,selectedProfileId); previewImage=r.image; }
    catch(err: unknown){ showToast(err instanceof Error ? err.message : 'Failed','error'); }
    finally { previewing=false; }
  }

  async function handleCancel(id: string) {
    try { await cancelJob(id); showToast('Cancelled','info'); }
    catch(err: unknown){ showToast(err instanceof Error ? err.message : 'Failed','error'); }
  }

  async function addBatchPage() {
    if(!selectedDeviceId||!selectedProfileId){ showToast('Select device & profile','error'); return; }
    batchScanning=true;
    try {
      const r=await previewScan(selectedDeviceId,selectedProfileId);
      batchPagePreviews=[...batchPagePreviews,r.image];
      batchPages=[...batchPages,`page_${batchPages.length+1}`];
      showToast(`Page ${batchPages.length} scanned`,'success');
    } catch(err: unknown){ showToast(err instanceof Error ? err.message : 'Failed','error'); }
    finally { batchScanning=false; }
  }

  function removeBatchPage(i: number) {
    batchPages=batchPages.filter((_,x)=>x!==i);
    batchPagePreviews=batchPagePreviews.filter((_,x)=>x!==i);
  }

  async function finishBatch() {
    if(!selectedDeviceId||!selectedTargetId||!selectedProfileId){ showToast('Select all fields','error'); return; }
    if(!batchPages.length){ showToast('Scan at least one page','error'); return; }
    batchFinishing=true;
    try {
      const resp=await startBatch({device_id:selectedDeviceId,profile_id:selectedProfileId,target_id:selectedTargetId,filename_prefix:filenamePrefix,page_paths:batchPages});
      const job=await getJob(resp.job_id);
      activeJob=job; recentJobs=[job,...recentJobs].slice(0,6);
      batchPages=[]; batchPagePreviews=[]; batchMode=false;
      showToast('Batch started','success');
    } catch(err: unknown){ showToast(err instanceof Error ? err.message : 'Failed','error'); }
    finally { batchFinishing=false; }
  }

  function sc(s: string) {
    return s==='completed'?'badge-success':s==='failed'?'badge-error':s==='running'?'badge-info':'badge-muted';
  }
  function fmtTime(ts: string|null) {
    if(!ts) return '—';
    const diff=Math.floor((Date.now()-new Date(ts).getTime())/1000);
    if(diff<60) return 'just now';
    if(diff<3600) return `${Math.floor(diff/60)}m ago`;
    if(diff<86400) return `${Math.floor(diff/3600)}h ago`;
    return new Date(ts).toLocaleDateString();
  }
</script>

<div class="page-wrap">
  {#if loading}
    <div style="display:flex;align-items:center;gap:10px;color:var(--c-text-2);padding:48px 0;">
      <Spinner /><span>Loading…</span>
    </div>
  {:else}
    <div style="display:flex;flex-direction:column;gap:16px;max-width:660px;">

      <!-- Scan form -->
      <div class="card">
        <div class="card-header">
          <span class="card-title"><ScanLine size={13} />New Scan</span>
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
            <span style="font-size:0.75rem;color:var(--c-text-2);">Batch</span>
            <div class="toggle"><input type="checkbox" bind:checked={batchMode} /><span class="toggle-slider"></span></div>
          </label>
        </div>

        <div class="card-body" style="display:flex;flex-direction:column;gap:14px;">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label" for="ds">Scanner</label>
              <select id="ds" class="form-control" bind:value={selectedDeviceId}>
                {#if !devices.length}<option value={null} disabled>No scanners</option>
                {:else}{#each sd as d}<option value={d.id}>{d.is_favorite?'★ ':''}{d.name}{d.online===false?' (offline)':''}</option>{/each}{/if}
              </select>
            </div>
            <div class="form-group">
              <label class="form-label" for="ts">Target</label>
              <select id="ts" class="form-control" bind:value={selectedTargetId}>
                {#if !targets.length}<option value={null} disabled>No targets</option>
                {:else}{#each st as t}<option value={t.id}>{t.is_favorite?'★ ':''}{t.name} ({t.type})</option>{/each}{/if}
              </select>
            </div>
            <div class="form-group">
              <label class="form-label" for="ps">Profile</label>
              <select id="ps" class="form-control" bind:value={selectedProfileId}>
                {#each profiles as p}<option value={p.id}>{p.name}</option>{/each}
              </select>
            </div>
            <div class="form-group">
              <label class="form-label" for="fn">Filename Prefix</label>
              <input id="fn" class="form-control" type="text" bind:value={filenamePrefix} placeholder="scan" />
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="wh">Webhook <span style="text-transform:none;font-weight:400;color:var(--c-text-3);">(optional)</span></label>
            <input id="wh" class="form-control" type="url" bind:value={webhookUrl} placeholder="https://…" />
          </div>

          {#if !batchMode}
            <div style="display:flex;gap:8px;flex-wrap:wrap;padding-top:2px;">
              <button class="btn-scan" style="flex:1;" onclick={handleScan}
                      disabled={scanning||!selectedDeviceId||!selectedTargetId}>
                {#if scanning}<Loader2 size={16} class="spin" />{:else}<Upload size={16} />{/if}
                Scan &amp; Upload
              </button>
              <button class="btn btn-secondary" onclick={handlePreview}
                      disabled={previewing||!selectedDeviceId}>
                {#if previewing}<Loader2 size={14} class="spin" />{:else}<Eye size={14} />{/if}
                Preview
              </button>
            </div>

            {#if previewImage}
              <div class="preview-wrap"><img src="data:image/jpeg;base64,{previewImage}" alt="Preview" /></div>
            {/if}
          {:else}
            <div style="display:flex;flex-direction:column;gap:10px;">
              <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <button class="btn btn-secondary" onclick={addBatchPage} disabled={batchScanning||!selectedDeviceId}>
                  {#if batchScanning}<Loader2 size={14} class="spin" />{:else}<Plus size={14} />{/if}
                  Scan Page
                </button>
                <span style="font-size:0.8125rem;color:var(--c-text-2);display:flex;align-items:center;gap:5px;">
                  <Layers size={13} />{batchPages.length} page{batchPages.length!==1?'s':''}
                </span>
              </div>
              {#if batchPagePreviews.length}
                <div class="thumb-strip">
                  {#each batchPagePreviews as prev, i}
                    <div class="thumb-item">
                      <img src="data:image/jpeg;base64,{prev}" alt="P{i+1}" />
                      <button class="thumb-remove" onclick={() => removeBatchPage(i)} aria-label="Remove"><X size={9} /></button>
                    </div>
                  {/each}
                </div>
              {/if}
              <button class="btn-scan" onclick={finishBatch}
                      disabled={batchFinishing||!batchPages.length||!selectedTargetId}>
                {#if batchFinishing}<Loader2 size={16} class="spin" />{:else}<Upload size={16} />{/if}
                Finish Batch &amp; Upload
              </button>
            </div>
          {/if}
        </div>
      </div>

      <!-- Active job -->
      {#if activeJob}
        <div class="card">
          <div class="card-header">
            <span class="card-title">
              {#if activeJob.status==='running'}<span class="dot-pulse"></span>
              {:else if activeJob.status==='completed'}<CheckCircle2 size={13} style="color:var(--c-ok);" />
              {:else if activeJob.status==='failed'}<XCircle size={13} style="color:var(--c-err);" />{/if}
              Job #{activeJob.id}
            </span>
            <span class="badge {sc(activeJob.status)}">{activeJob.status}</span>
          </div>
          <div class="card-body" style="display:flex;flex-direction:column;gap:10px;">
            {#if activeJob.status==='running'}
              <div style="display:flex;align-items:center;gap:8px;font-size:0.8125rem;color:var(--c-text-2);">
                <Loader2 size={13} class="spin" style="color:var(--c-accent);" />Scanning…
              </div>
              <div class="progress-track"><div class="progress-fill" style="width:60%;animation:progressPulse 2s ease-in-out infinite;"></div></div>
            {/if}
            {#if activeJob.message}<p style="font-size:0.8125rem;color:var(--c-err);">{activeJob.message}</p>{/if}
            {#if activeJob.status==='running'||activeJob.status==='queued'}
              <button class="btn btn-danger btn-sm" style="width:fit-content;" onclick={() => handleCancel(activeJob!.id)}>
                <X size={12} />Cancel
              </button>
            {/if}
          </div>
        </div>
      {/if}

      <!-- Recent jobs -->
      <div class="card">
        <div class="card-header">
          <span class="card-title"><Clock size={13} />Recent Jobs</span>
          <a href="/history" style="font-size:0.75rem;color:var(--c-text-2);display:flex;align-items:center;gap:3px;">
            View all <ChevronRight size={12} />
          </a>
        </div>
        {#if !recentJobs.length}
          <div class="empty-state" style="padding:32px 16px;">
            <ScanLine size={28} style="color:var(--c-surface-3);" />
            <p>No jobs yet — start a scan above.</p>
          </div>
        {:else}
          {#each recentJobs as job}
            <div style="display:flex;align-items:center;gap:10px;padding:10px 16px;border-bottom:1px solid var(--c-border);" class:last-item={false}>
              <span class="{job.status==='completed'?'dot-online':job.status==='failed'?'dot-offline':job.status==='running'?'dot-pulse':'dot-unknown'}"></span>
              <div style="flex:1;min-width:0;">
                <p style="font-size:0.8125rem;color:var(--c-text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{job.filename_prefix??'scan'}_{job.id}</p>
                <p style="font-size:0.75rem;color:var(--c-text-3);">{job.profile_id}</p>
              </div>
              <span class="badge {sc(job.status)}">{job.status}</span>
              <span style="font-size:0.75rem;color:var(--c-text-3);flex-shrink:0;">{fmtTime(job.created_at)}</span>
              {#if job.status==='running'||job.status==='queued'}
                <button class="btn btn-ghost btn-icon btn-sm" onclick={() => handleCancel(job.id)}><X size={12} /></button>
              {/if}
            </div>
          {/each}
        {/if}
      </div>

    </div>
  {/if}
</div>

<style>
  :global(.spin) { animation: spin 0.7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes progressPulse { 0%{width:15%} 50%{width:75%} 100%{width:15%} }
</style>
