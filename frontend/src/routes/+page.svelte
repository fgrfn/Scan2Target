<script lang="ts">
  import { onMount } from 'svelte';
  import { wsStore } from '$lib/stores/ws.svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import { listDevices, type Device } from '$lib/api/devices';
  import { listTargets, type Target } from '$lib/api/targets';
  import {
    getProfiles,
    startScan,
    listJobs,
    cancelJob,
    previewScan,
    startBatch,
    type ScanProfile,
    type Job
  } from '$lib/api/scan';
  import Spinner from '$lib/components/ui/Spinner.svelte';

  // Data
  let devices = $state<Device[]>([]);
  let targets = $state<Target[]>([]);
  let profiles = $state<ScanProfile[]>([]);
  let recentJobs = $state<Job[]>([]);

  // Form state
  let selectedDeviceId = $state<number | null>(null);
  let selectedTargetId = $state<number | null>(null);
  let selectedProfileId = $state<string>('');
  let filenamePrefix = $state('scan');
  let webhookUrl = $state('');

  // UI state
  let loading = $state(true);
  let scanning = $state(false);
  let previewing = $state(false);
  let previewImage = $state<string | null>(null);
  let activeJob = $state<Job | null>(null);

  // Batch mode
  let batchMode = $state(false);
  let batchPages = $state<string[]>([]); // page file paths from scan
  let batchPagePreviews = $state<string[]>([]); // base64 previews
  let batchScanning = $state(false);
  let batchFinishing = $state(false);

  // Sorted lists: favorites first
  const sortedDevices = $derived(
    [...devices].sort((a, b) => Number(b.is_favorite) - Number(a.is_favorite))
  );
  const sortedTargets = $derived(
    [...targets].sort((a, b) => Number(b.is_favorite) - Number(a.is_favorite))
  );

  onMount(async () => {
    try {
      const [d, t, p, j] = await Promise.all([
        listDevices(),
        listTargets(),
        getProfiles(),
        listJobs()
      ]);
      devices = d;
      targets = t;
      profiles = p;
      recentJobs = j.slice(0, 5);

      if (sortedDevices.length) selectedDeviceId = sortedDevices[0].id;
      if (sortedTargets.length) selectedTargetId = sortedTargets[0].id;
      if (p.length) selectedProfileId = p[0].id;
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load data', 'error');
    } finally {
      loading = false;
    }
  });

  // React to WebSocket job updates
  $effect(() => {
    const upd = wsStore.lastJobUpdate;
    if (!upd) return;
    if (activeJob && upd.id === activeJob.id) {
      activeJob = upd;
    }
    // Update recent jobs list
    recentJobs = recentJobs.map((j) => (j.id === upd.id ? upd : j));
  });

  async function handleScan() {
    if (!selectedDeviceId || !selectedTargetId || !selectedProfileId) {
      showToast('Please select a device, target and profile', 'error');
      return;
    }
    scanning = true;
    previewImage = null;
    activeJob = null;
    try {
      const job = await startScan({
        device_id: selectedDeviceId,
        profile_id: selectedProfileId,
        target_id: selectedTargetId,
        filename_prefix: filenamePrefix,
        webhook_url: webhookUrl || undefined
      });
      activeJob = job;
      recentJobs = [job, ...recentJobs].slice(0, 5);
      showToast('Scan job started', 'success');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to start scan', 'error');
    } finally {
      scanning = false;
    }
  }

  async function handlePreview() {
    if (!selectedDeviceId || !selectedProfileId) {
      showToast('Please select a device and profile', 'error');
      return;
    }
    previewing = true;
    previewImage = null;
    try {
      const resp = await previewScan(selectedDeviceId, selectedProfileId);
      previewImage = resp.image;
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Preview failed', 'error');
    } finally {
      previewing = false;
    }
  }

  async function handleCancelJob(id: number) {
    try {
      await cancelJob(id);
      showToast('Job cancelled', 'info');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Cancel failed', 'error');
    }
  }

  // Batch mode
  async function addBatchPage() {
    if (!selectedDeviceId || !selectedProfileId) {
      showToast('Please select a device and profile', 'error');
      return;
    }
    batchScanning = true;
    try {
      const resp = await previewScan(selectedDeviceId, selectedProfileId);
      // Store preview image as a stand-in for the page path
      batchPagePreviews = [...batchPagePreviews, resp.image];
      batchPages = [...batchPages, `page_${batchPages.length + 1}`];
      showToast(`Page ${batchPages.length} scanned`, 'success');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Scan failed', 'error');
    } finally {
      batchScanning = false;
    }
  }

  function removeBatchPage(index: number) {
    batchPages = batchPages.filter((_, i) => i !== index);
    batchPagePreviews = batchPagePreviews.filter((_, i) => i !== index);
  }

  async function finishBatch() {
    if (!selectedDeviceId || !selectedTargetId || !selectedProfileId) {
      showToast('Please select a device, target and profile', 'error');
      return;
    }
    if (batchPages.length === 0) {
      showToast('Scan at least one page first', 'error');
      return;
    }
    batchFinishing = true;
    try {
      const job = await startBatch({
        device_id: selectedDeviceId,
        profile_id: selectedProfileId,
        target_id: selectedTargetId,
        filename_prefix: filenamePrefix,
        page_paths: batchPages
      });
      activeJob = job;
      recentJobs = [job, ...recentJobs].slice(0, 5);
      batchPages = [];
      batchPagePreviews = [];
      batchMode = false;
      showToast('Batch job started', 'success');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Batch failed', 'error');
    } finally {
      batchFinishing = false;
    }
  }

  function statusBadgeClass(status: string) {
    switch (status) {
      case 'completed': return 'badge-success';
      case 'failed': return 'badge-error';
      case 'running': return 'badge-info';
      case 'queued': return 'badge-muted';
      case 'cancelled': return 'badge-muted';
      default: return 'badge-muted';
    }
  }

  function formatTime(ts: string | null) {
    if (!ts) return '—';
    return new Date(ts).toLocaleString();
  }
</script>

<div class="page-header">
  <h1 class="page-title">🖨 Scan</h1>
  <p class="page-subtitle">Scan a document and deliver it to a configured target</p>
</div>

<div class="page-body">
  {#if loading}
    <div class="flex items-center gap-3">
      <Spinner />
      <span class="text-muted">Loading…</span>
    </div>
  {:else}
    <div class="scan-layout">
      <!-- Main scan form -->
      <div class="card">
        <h2 class="card-title">📄 New Scan</h2>

        <div class="form-group">
          <label class="form-label" for="device-select">Scanner</label>
          <select id="device-select" class="form-control" bind:value={selectedDeviceId}>
            {#if devices.length === 0}
              <option value={null} disabled>No scanners configured</option>
            {:else}
              {#each sortedDevices as d}
                <option value={d.id}>
                  {d.is_favorite ? '★ ' : ''}{d.name}
                  {d.is_online === false ? ' (offline)' : ''}
                </option>
              {/each}
            {/if}
          </select>
        </div>

        <div class="form-group">
          <label class="form-label" for="target-select">Target</label>
          <select id="target-select" class="form-control" bind:value={selectedTargetId}>
            {#if targets.length === 0}
              <option value={null} disabled>No targets configured</option>
            {:else}
              {#each sortedTargets as t}
                <option value={t.id}>
                  {t.is_favorite ? '★ ' : ''}{t.name} ({t.type})
                </option>
              {/each}
            {/if}
          </select>
        </div>

        <div class="form-group">
          <label class="form-label" for="profile-select">Scan Profile</label>
          <select id="profile-select" class="form-control" bind:value={selectedProfileId}>
            {#each profiles as p}
              <option value={p.id}>{p.name}</option>
            {/each}
          </select>
        </div>

        <div class="form-group">
          <label class="form-label" for="filename-input">Filename Prefix</label>
          <input
            id="filename-input"
            class="form-control"
            type="text"
            bind:value={filenamePrefix}
            placeholder="scan"
          />
          <p class="form-hint">A timestamp will be appended automatically.</p>
        </div>

        <div class="form-group">
          <label class="form-label" for="webhook-input">Webhook URL (optional)</label>
          <input
            id="webhook-input"
            class="form-control"
            type="url"
            bind:value={webhookUrl}
            placeholder="https://…"
          />
        </div>

        <!-- Batch mode toggle -->
        <div class="form-group">
          <div class="toggle-wrap">
            <label class="toggle" for="batch-toggle">
              <input id="batch-toggle" type="checkbox" bind:checked={batchMode} />
              <span class="toggle-slider"></span>
            </label>
            <span class="form-label" style="margin-bottom:0">Batch / Multi-page mode</span>
          </div>
        </div>

        {#if !batchMode}
          <!-- Single scan -->
          <div class="btn-row">
            <button
              class="btn btn-primary btn-lg"
              onclick={handleScan}
              disabled={scanning || !selectedDeviceId || !selectedTargetId}
            >
              {#if scanning}<Spinner size="sm" />{/if}
              Scan & Upload
            </button>
            <button
              class="btn btn-secondary"
              onclick={handlePreview}
              disabled={previewing || !selectedDeviceId}
            >
              {#if previewing}<Spinner size="sm" />{/if}
              Preview
            </button>
          </div>

          {#if previewImage}
            <div class="preview-wrap" style="margin-top:16px">
              <img src="data:image/jpeg;base64,{previewImage}" alt="Scan preview" />
            </div>
          {/if}
        {:else}
          <!-- Batch mode -->
          <div class="batch-section">
            <div class="batch-actions">
              <button
                class="btn btn-secondary"
                onclick={addBatchPage}
                disabled={batchScanning || !selectedDeviceId}
              >
                {#if batchScanning}<Spinner size="sm" />{/if}
                + Scan Page
              </button>
              <span class="text-muted" style="font-size:0.85rem">
                {batchPages.length} page{batchPages.length !== 1 ? 's' : ''} scanned
              </span>
            </div>

            {#if batchPagePreviews.length > 0}
              <div class="thumb-strip">
                {#each batchPagePreviews as preview, i}
                  <div class="thumb-item">
                    <img src="data:image/jpeg;base64,{preview}" alt="Page {i + 1}" />
                    <button class="thumb-remove" onclick={() => removeBatchPage(i)} aria-label="Remove page {i + 1}">
                      ✕
                    </button>
                  </div>
                {/each}
              </div>
            {/if}

            <button
              class="btn btn-primary btn-lg"
              style="margin-top:14px"
              onclick={finishBatch}
              disabled={batchFinishing || batchPages.length === 0 || !selectedTargetId}
            >
              {#if batchFinishing}<Spinner size="sm" />{/if}
              Finish Batch & Upload
            </button>
          </div>
        {/if}
      </div>

      <!-- Active job status -->
      {#if activeJob}
        <div class="card">
          <h2 class="card-title">⏳ Active Job</h2>
          <div class="job-status-block">
            <div class="flex items-center gap-3">
              <span class="badge {statusBadgeClass(activeJob.status)}">{activeJob.status}</span>
              <span class="text-muted" style="font-size:0.85rem">Job #{activeJob.id}</span>
            </div>
            {#if activeJob.status === 'running'}
              <div class="flex items-center gap-2" style="margin-top:8px">
                <Spinner size="sm" />
                <span class="text-muted" style="font-size:0.85rem">Scanning…</span>
              </div>
            {/if}
            {#if activeJob.error}
              <p class="text-error" style="margin-top:8px;font-size:0.85rem">{activeJob.error}</p>
            {/if}
            {#if activeJob.status === 'running' || activeJob.status === 'queued'}
              <button
                class="btn btn-danger btn-sm"
                style="margin-top:10px"
                onclick={() => handleCancelJob(activeJob!.id)}
              >
                Cancel
              </button>
            {/if}
          </div>
        </div>
      {/if}

      <!-- Recent jobs -->
      <div class="card">
        <h2 class="card-title">🕐 Recent Jobs</h2>
        {#if recentJobs.length === 0}
          <div class="empty-state">
            <div class="empty-icon">📭</div>
            <p>No jobs yet. Start a scan above!</p>
          </div>
        {:else}
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Status</th>
                  <th>Profile</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {#each recentJobs as job}
                  <tr>
                    <td class="font-mono" style="font-size:0.8rem">#{job.id}</td>
                    <td><span class="badge {statusBadgeClass(job.status)}">{job.status}</span></td>
                    <td style="font-size:0.8rem;color:var(--color-text-muted)">{job.profile_id}</td>
                    <td style="font-size:0.8rem;color:var(--color-text-muted)">{formatTime(job.created_at)}</td>
                    <td>
                      {#if job.status === 'running' || job.status === 'queued'}
                        <button class="btn btn-danger btn-sm" onclick={() => handleCancelJob(job.id)}>
                          Cancel
                        </button>
                      {/if}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .scan-layout {
    display: flex;
    flex-direction: column;
    gap: 20px;
    max-width: 680px;
  }

  .btn-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
    margin-top: 4px;
  }

  .batch-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .batch-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .job-status-block {
    padding: 12px;
    background: var(--color-bg);
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
  }
</style>
