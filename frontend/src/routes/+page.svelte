<script lang="ts">
  import { onMount } from 'svelte';
  import { wsStore } from '$lib/stores/ws.svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import { listDevices, type Device } from '$lib/api/devices';
  import { listTargets, type Target } from '$lib/api/targets';
  import {
    getProfiles, startScan, listJobs, cancelJob, previewScan, startBatch,
    type ScanProfile, type Job
  } from '$lib/api/scan';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import { ScanLine, Eye, Upload, Plus, X, CheckCircle2, XCircle, Loader2,
           Clock, Layers, ChevronRight } from 'lucide-svelte';

  let devices      = $state<Device[]>([]);
  let targets      = $state<Target[]>([]);
  let profiles     = $state<ScanProfile[]>([]);
  let recentJobs   = $state<Job[]>([]);
  let loading      = $state(true);
  let scanning     = $state(false);
  let previewing   = $state(false);
  let previewImage = $state<string | null>(null);
  let activeJob    = $state<Job | null>(null);

  let selectedDeviceId  = $state<number | null>(null);
  let selectedTargetId  = $state<number | null>(null);
  let selectedProfileId = $state<string>('');
  let filenamePrefix    = $state('scan');
  let webhookUrl        = $state('');
  let batchMode         = $state(false);
  let batchPages        = $state<string[]>([]);
  let batchPagePreviews = $state<string[]>([]);
  let batchScanning     = $state(false);
  let batchFinishing    = $state(false);

  const sortedDevices = $derived([...devices].sort((a,b) => Number(b.is_favorite)-Number(a.is_favorite)));
  const sortedTargets = $derived([...targets].sort((a,b) => Number(b.is_favorite)-Number(a.is_favorite)));

  onMount(async () => {
    try {
      const [d, t, p, j] = await Promise.all([listDevices(), listTargets(), getProfiles(), listJobs()]);
      devices = d; targets = t; profiles = p;
      recentJobs = j.slice(0, 6);
      if (sortedDevices.length)  selectedDeviceId  = sortedDevices[0].id;
      if (sortedTargets.length)  selectedTargetId  = sortedTargets[0].id;
      if (p.length)              selectedProfileId = p[0].id;
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load data', 'error');
    } finally { loading = false; }
  });

  $effect(() => {
    const upd = wsStore.lastJobUpdate;
    if (!upd) return;
    if (activeJob && upd.id === activeJob.id) activeJob = upd;
    recentJobs = recentJobs.map(j => j.id === upd.id ? upd : j);
  });

  async function handleScan() {
    if (!selectedDeviceId || !selectedTargetId || !selectedProfileId) {
      showToast('Select a device, target and profile', 'error'); return;
    }
    scanning = true; previewImage = null; activeJob = null;
    try {
      const job = await startScan({
        device_id: selectedDeviceId, profile_id: selectedProfileId,
        target_id: selectedTargetId, filename_prefix: filenamePrefix,
        webhook_url: webhookUrl || undefined
      });
      activeJob = job;
      recentJobs = [job, ...recentJobs].slice(0, 6);
      showToast('Scan started', 'success');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Scan failed', 'error');
    } finally { scanning = false; }
  }

  async function handlePreview() {
    if (!selectedDeviceId || !selectedProfileId) {
      showToast('Select a device and profile', 'error'); return;
    }
    previewing = true; previewImage = null;
    try {
      const resp = await previewScan(selectedDeviceId, selectedProfileId);
      previewImage = resp.image;
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Preview failed', 'error');
    } finally { previewing = false; }
  }

  async function handleCancelJob(id: number) {
    try { await cancelJob(id); showToast('Job cancelled', 'info'); }
    catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Cancel failed', 'error'); }
  }

  async function addBatchPage() {
    if (!selectedDeviceId || !selectedProfileId) {
      showToast('Select a device and profile', 'error'); return;
    }
    batchScanning = true;
    try {
      const resp = await previewScan(selectedDeviceId, selectedProfileId);
      batchPagePreviews = [...batchPagePreviews, resp.image];
      batchPages = [...batchPages, `page_${batchPages.length + 1}`];
      showToast(`Page ${batchPages.length} scanned`, 'success');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Scan failed', 'error');
    } finally { batchScanning = false; }
  }

  function removeBatchPage(index: number) {
    batchPages = batchPages.filter((_, i) => i !== index);
    batchPagePreviews = batchPagePreviews.filter((_, i) => i !== index);
  }

  async function finishBatch() {
    if (!selectedDeviceId || !selectedTargetId || !selectedProfileId) {
      showToast('Select device, target and profile', 'error'); return;
    }
    if (batchPages.length === 0) { showToast('Scan at least one page first', 'error'); return; }
    batchFinishing = true;
    try {
      const job = await startBatch({
        device_id: selectedDeviceId, profile_id: selectedProfileId,
        target_id: selectedTargetId, filename_prefix: filenamePrefix,
        page_paths: batchPages
      });
      activeJob = job;
      recentJobs = [job, ...recentJobs].slice(0, 6);
      batchPages = []; batchPagePreviews = []; batchMode = false;
      showToast('Batch upload started', 'success');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Batch failed', 'error');
    } finally { batchFinishing = false; }
  }

  function statusClass(s: string) {
    return s === 'completed' ? 'badge-success'
         : s === 'failed'    ? 'badge-error'
         : s === 'running'   ? 'badge-info'
         : 'badge-muted';
  }

  function statusDotClass(s: string) {
    return s === 'completed' ? 'dot-online'
         : s === 'failed'    ? 'bg-red-500 inline-block rounded-full w-2 h-2'
         : s === 'running'   ? 'dot-pulse'
         : 'dot-unknown';
  }

  function fmtTime(ts: string | null) {
    if (!ts) return '—';
    const d = new Date(ts);
    const now = new Date();
    const diff = Math.floor((now.getTime() - d.getTime()) / 1000);
    if (diff < 60)  return 'just now';
    if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
    return d.toLocaleDateString();
  }
</script>

<div class="page-wrap">

  {#if loading}
    <div class="flex items-center gap-3 text-zinc-500 py-12">
      <Spinner /><span>Loading…</span>
    </div>
  {:else}
    <div class="grid gap-5" style="grid-template-columns: 1fr; max-width: 680px;">

      <!-- ── Scan form card ── -->
      <div class="card">
        <!-- Header -->
        <div class="card-header">
          <span class="card-title flex items-center gap-2">
            <ScanLine size={15} class="text-indigo-400" />
            New Scan
          </span>
          <!-- Batch toggle -->
          <label class="flex items-center gap-2 cursor-pointer">
            <span class="text-xs text-zinc-500">Batch</span>
            <div class="toggle" title="Batch / multi-page mode">
              <input type="checkbox" bind:checked={batchMode} />
              <span class="toggle-slider"></span>
            </div>
          </label>
        </div>

        <div class="card-body flex flex-col gap-4">
          <!-- 2-col selectors -->
          <div class="form-row">
            <div class="form-group">
              <label class="form-label" for="dev-sel">Scanner</label>
              <select id="dev-sel" class="form-control" bind:value={selectedDeviceId}>
                {#if devices.length === 0}
                  <option value={null} disabled>No scanners</option>
                {:else}
                  {#each sortedDevices as d}
                    <option value={d.id}>{d.is_favorite ? '★ ' : ''}{d.name}{d.is_online === false ? ' (offline)' : ''}</option>
                  {/each}
                {/if}
              </select>
            </div>

            <div class="form-group">
              <label class="form-label" for="tgt-sel">Target</label>
              <select id="tgt-sel" class="form-control" bind:value={selectedTargetId}>
                {#if targets.length === 0}
                  <option value={null} disabled>No targets</option>
                {:else}
                  {#each sortedTargets as t}
                    <option value={t.id}>{t.is_favorite ? '★ ' : ''}{t.name} ({t.type})</option>
                  {/each}
                {/if}
              </select>
            </div>

            <div class="form-group">
              <label class="form-label" for="prof-sel">Profile</label>
              <select id="prof-sel" class="form-control" bind:value={selectedProfileId}>
                {#each profiles as p}
                  <option value={p.id}>{p.name}</option>
                {/each}
              </select>
            </div>

            <div class="form-group">
              <label class="form-label" for="fname">Filename Prefix</label>
              <input id="fname" class="form-control" type="text"
                     bind:value={filenamePrefix} placeholder="scan" />
            </div>
          </div>

          <!-- Webhook (optional, collapsed) -->
          <div class="form-group">
            <label class="form-label" for="webhook">Webhook URL <span class="normal-case text-zinc-600">(optional)</span></label>
            <input id="webhook" class="form-control" type="url"
                   bind:value={webhookUrl} placeholder="https://…" />
          </div>

          <!-- ── Single mode actions ── -->
          {#if !batchMode}
            <div class="flex gap-3 flex-wrap pt-1">
              <button class="btn-scan flex-1" onclick={handleScan}
                      disabled={scanning || !selectedDeviceId || !selectedTargetId}>
                {#if scanning}
                  <Loader2 size={18} class="animate-spin" />
                {:else}
                  <Upload size={18} />
                {/if}
                Scan & Upload
              </button>
              <button class="btn btn-secondary" onclick={handlePreview}
                      disabled={previewing || !selectedDeviceId}>
                {#if previewing}<Loader2 size={15} class="animate-spin" />{:else}<Eye size={15} />{/if}
                Preview
              </button>
            </div>

            {#if previewImage}
              <div class="preview-wrap mt-1">
                <img src="data:image/jpeg;base64,{previewImage}" alt="Scan preview" />
              </div>
            {/if}

          <!-- ── Batch mode ── -->
          {:else}
            <div class="flex flex-col gap-3">
              <div class="flex items-center gap-3 flex-wrap">
                <button class="btn btn-secondary" onclick={addBatchPage}
                        disabled={batchScanning || !selectedDeviceId}>
                  {#if batchScanning}<Loader2 size={15} class="animate-spin" />{:else}<Plus size={15} />{/if}
                  Scan Page
                </button>
                <span class="text-sm text-zinc-500 flex items-center gap-1.5">
                  <Layers size={13} />
                  {batchPages.length} page{batchPages.length !== 1 ? 's' : ''}
                </span>
              </div>

              {#if batchPagePreviews.length > 0}
                <div class="thumb-strip">
                  {#each batchPagePreviews as preview, i}
                    <div class="thumb-item">
                      <img src="data:image/jpeg;base64,{preview}" alt="Page {i+1}" />
                      <button class="thumb-remove" onclick={() => removeBatchPage(i)}
                              aria-label="Remove page {i+1}">
                        <X size={10} />
                      </button>
                    </div>
                  {/each}
                </div>
              {/if}

              <button class="btn-scan" onclick={finishBatch}
                      disabled={batchFinishing || batchPages.length === 0 || !selectedTargetId}>
                {#if batchFinishing}<Loader2 size={18} class="animate-spin" />{:else}<Upload size={18} />{/if}
                Finish Batch & Upload
              </button>
            </div>
          {/if}
        </div>
      </div>

      <!-- ── Active job card ── -->
      {#if activeJob}
        <div class="card overflow-hidden">
          <div class="card-header">
            <span class="card-title flex items-center gap-2">
              {#if activeJob.status === 'running'}
                <span class="dot-pulse"></span>
              {:else if activeJob.status === 'completed'}
                <CheckCircle2 size={14} class="text-emerald-400" />
              {:else if activeJob.status === 'failed'}
                <XCircle size={14} class="text-red-400" />
              {/if}
              Job #{activeJob.id}
            </span>
            <span class="badge {statusClass(activeJob.status)}">{activeJob.status}</span>
          </div>
          <div class="card-body">
            {#if activeJob.status === 'running'}
              <div class="flex items-center gap-2 text-sm text-zinc-400">
                <Loader2 size={14} class="animate-spin text-indigo-400" />
                Scanning…
              </div>
              <!-- Animated progress bar -->
              <div class="progress-track mt-3">
                <div class="progress-fill" style="width: 60%; animation: progressPulse 2s ease-in-out infinite;"></div>
              </div>
            {/if}
            {#if activeJob.error}
              <p class="text-sm text-red-400 mt-1">{activeJob.error}</p>
            {/if}
            {#if activeJob.status === 'running' || activeJob.status === 'queued'}
              <button class="btn btn-danger btn-sm mt-3" onclick={() => handleCancelJob(activeJob!.id)}>
                <X size={12} /> Cancel
              </button>
            {/if}
          </div>
        </div>
      {/if}

      <!-- ── Recent jobs ── -->
      <div class="card">
        <div class="card-header">
          <span class="card-title flex items-center gap-2">
            <Clock size={14} class="text-zinc-500" />
            Recent Jobs
          </span>
          <a href="/history" class="text-xs text-zinc-500 hover:text-zinc-300 flex items-center gap-1 transition-colors" style="text-decoration:none">
            View all <ChevronRight size={12} />
          </a>
        </div>

        {#if recentJobs.length === 0}
          <div class="empty-state">
            <ScanLine size={32} class="text-zinc-800" />
            <p>No jobs yet — start a scan above.</p>
          </div>
        {:else}
          <div class="flex flex-col divide-y divide-zinc-800/60">
            {#each recentJobs as job}
              <div class="flex items-center gap-3 px-5 py-3">
                <span class="{statusDotClass(job.status)} flex-shrink-0"></span>
                <div class="flex-1 min-w-0">
                  <p class="text-sm text-zinc-200 truncate">
                    {job.filename_prefix ?? 'scan'}_{job.id}
                  </p>
                  <p class="text-xs text-zinc-600">{job.profile_id}</p>
                </div>
                <div class="flex items-center gap-2 flex-shrink-0">
                  <span class="badge {statusClass(job.status)}">{job.status}</span>
                  <span class="text-xs text-zinc-600">{fmtTime(job.created_at)}</span>
                  {#if job.status === 'running' || job.status === 'queued'}
                    <button class="btn btn-ghost btn-icon btn-sm text-zinc-600 hover:text-red-400"
                            onclick={() => handleCancelJob(job.id)}>
                      <X size={12} />
                    </button>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

    </div>
  {/if}
</div>

<style>
  @keyframes progressPulse {
    0%   { width: 20%; }
    50%  { width: 80%; }
    100% { width: 20%; }
  }
  :global(.animate-spin) { animation: spin 0.75s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
