<script lang="ts">
  import { onMount } from 'svelte';
  import { wsStore } from '$lib/stores/ws.svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import { listHistory, clearHistory, deleteHistoryItem, cancelHistoryJob, retryUpload } from '$lib/api/history';
  import type { Job } from '$lib/api/scan';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import { Clock, CheckCircle2, XCircle, Loader2, RotateCcw, X, Trash2, History } from 'lucide-svelte';

  let jobs       = $state<Job[]>([]);
  let loading    = $state(true);
  let clearing   = $state(false);

  let cancellingIds = $state<Set<number>>(new Set());
  let retryingIds   = $state<Set<number>>(new Set());
  let deletingIds   = $state<Set<number>>(new Set());

  onMount(() => loadHistory());

  $effect(() => {
    const upd = wsStore.lastJobUpdate;
    if (!upd) return;
    const idx = jobs.findIndex(j => j.id === upd.id);
    if (idx !== -1) jobs = jobs.map(j => j.id === upd.id ? upd : j);
    else jobs = [upd, ...jobs];
  });

  async function loadHistory() {
    loading = true;
    try { jobs = await listHistory(); }
    catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Failed', 'error'); }
    finally { loading = false; }
  }

  async function handleClearAll() {
    if (!confirm('Clear all job history? This cannot be undone.')) return;
    clearing = true;
    try { await clearHistory(); jobs = []; showToast('History cleared', 'info'); }
    catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Failed', 'error'); }
    finally { clearing = false; }
  }

  async function handleCancel(id: number) {
    cancellingIds = new Set([...cancellingIds, id]);
    try {
      await cancelHistoryJob(id);
      jobs = jobs.map(j => j.id === id ? { ...j, status: 'cancelled' as Job['status'] } : j);
      showToast('Job cancelled', 'info');
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Failed', 'error'); }
    finally { cancellingIds.delete(id); cancellingIds = new Set(cancellingIds); }
  }

  async function handleRetry(id: number) {
    retryingIds = new Set([...retryingIds, id]);
    try {
      const updated = await retryUpload(id);
      jobs = jobs.map(j => j.id === id ? updated : j);
      showToast('Retry upload started', 'success');
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Failed', 'error'); }
    finally { retryingIds.delete(id); retryingIds = new Set(retryingIds); }
  }

  async function handleDelete(id: number) {
    deletingIds = new Set([...deletingIds, id]);
    try { await deleteHistoryItem(id); jobs = jobs.filter(j => j.id !== id); showToast('Entry deleted', 'info'); }
    catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Failed', 'error'); }
    finally { deletingIds.delete(id); deletingIds = new Set(deletingIds); }
  }

  function fmtDate(ts: string | null) {
    if (!ts) return '—';
    const d = new Date(ts);
    const now = new Date();
    const diff = Math.floor((now.getTime() - d.getTime()) / 1000);
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
    return d.toLocaleDateString(undefined, { month:'short', day:'numeric', year:'numeric' });
  }

  function statusColor(s: string) {
    return s === 'completed' ? 'border-emerald-500/40'
         : s === 'failed'    ? 'border-red-500/40'
         : s === 'running'   ? 'border-indigo-500/40'
         : 'border-zinc-700/40';
  }
</script>

<div class="page-wrap">
  <div class="page-header">
    <div>
      <h1 class="page-title">History</h1>
      <p class="page-sub">All scan jobs and results</p>
    </div>
    <button class="btn btn-secondary btn-sm" onclick={handleClearAll} disabled={clearing || jobs.length === 0}>
      {#if clearing}<Loader2 size={13} class="animate-spin" />{:else}<Trash2 size={13} />{/if}
      Clear All
    </button>
  </div>

  {#if loading}
    <div class="flex items-center gap-3 text-zinc-500 py-12"><Spinner /><span>Loading…</span></div>
  {:else if jobs.length === 0}
    <div class="card">
      <div class="empty-state">
        <History size={40} class="text-zinc-800" />
        <p>No job history yet.<br />Start a scan to see results here.</p>
      </div>
    </div>
  {:else}
    <!-- Desktop table view -->
    <div class="card hidden md:block">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Status</th>
              <th>ID</th>
              <th>Device</th>
              <th>Target</th>
              <th>Profile</th>
              <th>Created</th>
              <th>Completed</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {#each jobs as job}
              <tr class:opacity-60={job.status === 'cancelled'}>
                <td>
                  <div class="flex items-center gap-2">
                    {#if job.status === 'completed'}
                      <CheckCircle2 size={14} class="text-emerald-400" />
                    {:else if job.status === 'failed'}
                      <XCircle size={14} class="text-red-400" />
                    {:else if job.status === 'running'}
                      <span class="dot-pulse"></span>
                    {:else}
                      <span class="dot-unknown"></span>
                    {/if}
                    <span class="badge {job.status === 'completed' ? 'badge-success' : job.status === 'failed' ? 'badge-error' : job.status === 'running' ? 'badge-info' : 'badge-muted'}">
                      {job.status}
                    </span>
                  </div>
                </td>
                <td class="font-mono text-zinc-500" style="font-size:0.8rem">#{job.id}</td>
                <td class="text-zinc-300" style="font-size:0.8rem">{job.device_name ?? job.device_id}</td>
                <td class="text-zinc-300" style="font-size:0.8rem">{job.target_name ?? job.target_id}</td>
                <td class="text-zinc-500" style="font-size:0.78rem">{job.profile_id}</td>
                <td class="text-zinc-500" style="font-size:0.78rem;white-space:nowrap">{fmtDate(job.created_at)}</td>
                <td class="text-zinc-500" style="font-size:0.78rem;white-space:nowrap">{fmtDate(job.completed_at)}</td>
                <td>
                  <div class="flex gap-1">
                    {#if job.status === 'running' || job.status === 'queued'}
                      <button class="btn btn-ghost btn-icon btn-sm hover:text-red-400"
                              onclick={() => handleCancel(job.id)} disabled={cancellingIds.has(job.id)}>
                        {#if cancellingIds.has(job.id)}<Loader2 size={12} class="animate-spin" />{:else}<X size={12} />{/if}
                      </button>
                    {/if}
                    {#if job.status === 'failed' && job.file_path}
                      <button class="btn btn-ghost btn-icon btn-sm hover:text-indigo-400"
                              onclick={() => handleRetry(job.id)} disabled={retryingIds.has(job.id)}>
                        {#if retryingIds.has(job.id)}<Loader2 size={12} class="animate-spin" />{:else}<RotateCcw size={12} />{/if}
                      </button>
                    {/if}
                    <button class="btn btn-ghost btn-icon btn-sm hover:text-red-400"
                            onclick={() => handleDelete(job.id)} disabled={deletingIds.has(job.id)}>
                      {#if deletingIds.has(job.id)}<Loader2 size={12} class="animate-spin" />{:else}<Trash2 size={12} />{/if}
                    </button>
                  </div>
                </td>
              </tr>
              {#if job.error}
                <tr>
                  <td colspan="8" class="pt-0 pb-2">
                    <div class="flex items-center gap-1.5 text-xs text-red-400 bg-red-500/5 rounded px-3 py-1.5 -mt-1">
                      <XCircle size={11} />
                      {job.error}
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Mobile card list -->
    <div class="flex flex-col gap-3 md:hidden">
      {#each jobs as job}
        <div class="card border-l-2 {statusColor(job.status)} overflow-hidden">
          <div class="p-4">
            <div class="flex items-start justify-between gap-2 mb-2">
              <div class="flex items-center gap-2">
                {#if job.status === 'completed'}
                  <CheckCircle2 size={15} class="text-emerald-400 flex-shrink-0" />
                {:else if job.status === 'failed'}
                  <XCircle size={15} class="text-red-400 flex-shrink-0" />
                {:else if job.status === 'running'}
                  <span class="dot-pulse flex-shrink-0"></span>
                {:else}
                  <Clock size={13} class="text-zinc-600 flex-shrink-0" />
                {/if}
                <p class="font-medium text-sm text-zinc-200">
                  {job.filename_prefix ?? 'scan'}_{job.id}
                </p>
              </div>
              <span class="text-xs text-zinc-600 flex-shrink-0">{fmtDate(job.created_at)}</span>
            </div>

            <div class="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-zinc-500 mb-3">
              <span>{job.device_name ?? job.device_id}</span>
              <span>→</span>
              <span>{job.target_name ?? job.target_id}</span>
              <span>•</span>
              <span>{job.profile_id}</span>
            </div>

            {#if job.error}
              <p class="text-xs text-red-400 bg-red-500/8 rounded px-2 py-1 mb-3">{job.error}</p>
            {/if}

            <div class="flex items-center gap-2">
              <span class="badge {job.status === 'completed' ? 'badge-success' : job.status === 'failed' ? 'badge-error' : job.status === 'running' ? 'badge-info' : 'badge-muted'}">
                {job.status}
              </span>
              <div class="flex gap-1 ml-auto">
                {#if job.status === 'running' || job.status === 'queued'}
                  <button class="btn btn-ghost btn-sm hover:text-red-400"
                          onclick={() => handleCancel(job.id)} disabled={cancellingIds.has(job.id)}>
                    <X size={13} /> Cancel
                  </button>
                {/if}
                {#if job.status === 'failed' && job.file_path}
                  <button class="btn btn-ghost btn-sm hover:text-indigo-400"
                          onclick={() => handleRetry(job.id)} disabled={retryingIds.has(job.id)}>
                    <RotateCcw size={13} /> Retry
                  </button>
                {/if}
                <button class="btn btn-ghost btn-sm hover:text-red-400"
                        onclick={() => handleDelete(job.id)} disabled={deletingIds.has(job.id)}>
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  :global(.animate-spin) { animation: spin 0.75s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
