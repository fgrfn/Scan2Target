<script lang="ts">
  import { onMount } from 'svelte';
  import { wsStore } from '$lib/stores/ws.svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import {
    listHistory,
    clearHistory,
    deleteHistoryItem,
    cancelHistoryJob,
    retryUpload
  } from '$lib/api/history';
  import type { Job } from '$lib/api/scan';
  import Spinner from '$lib/components/ui/Spinner.svelte';

  let jobs = $state<Job[]>([]);
  let loading = $state(true);
  let clearing = $state(false);

  let cancellingIds = $state<Set<number>>(new Set());
  let retryingIds = $state<Set<number>>(new Set());
  let deletingIds = $state<Set<number>>(new Set());

  onMount(async () => {
    await loadHistory();
  });

  $effect(() => {
    const upd = wsStore.lastJobUpdate;
    if (!upd) return;
    const idx = jobs.findIndex((j) => j.id === upd.id);
    if (idx !== -1) {
      jobs = jobs.map((j) => (j.id === upd.id ? upd : j));
    } else {
      jobs = [upd, ...jobs];
    }
  });

  async function loadHistory() {
    loading = true;
    try {
      jobs = await listHistory();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load history', 'error');
    } finally {
      loading = false;
    }
  }

  async function handleClearAll() {
    if (!confirm('Clear all job history? This cannot be undone.')) return;
    clearing = true;
    try {
      await clearHistory();
      jobs = [];
      showToast('History cleared', 'info');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to clear history', 'error');
    } finally {
      clearing = false;
    }
  }

  async function handleCancel(id: number) {
    cancellingIds = new Set([...cancellingIds, id]);
    try {
      await cancelHistoryJob(id);
      jobs = jobs.map((j) =>
        j.id === id ? { ...j, status: 'cancelled' as Job['status'] } : j
      );
      showToast('Job cancelled', 'info');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Cancel failed', 'error');
    } finally {
      cancellingIds.delete(id);
      cancellingIds = new Set(cancellingIds);
    }
  }

  async function handleRetry(id: number) {
    retryingIds = new Set([...retryingIds, id]);
    try {
      const updated = await retryUpload(id);
      jobs = jobs.map((j) => (j.id === id ? updated : j));
      showToast('Retry upload started', 'success');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Retry failed', 'error');
    } finally {
      retryingIds.delete(id);
      retryingIds = new Set(retryingIds);
    }
  }

  async function handleDelete(id: number) {
    deletingIds = new Set([...deletingIds, id]);
    try {
      await deleteHistoryItem(id);
      jobs = jobs.filter((j) => j.id !== id);
      showToast('Entry deleted', 'info');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Delete failed', 'error');
    } finally {
      deletingIds.delete(id);
      deletingIds = new Set(deletingIds);
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

  function formatDate(ts: string | null) {
    if (!ts) return '—';
    return new Date(ts).toLocaleString();
  }
</script>

<div class="page-header">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="page-title">📋 History</h1>
      <p class="page-subtitle">All scan jobs and their results</p>
    </div>
    <button
      class="btn btn-danger btn-sm"
      onclick={handleClearAll}
      disabled={clearing || jobs.length === 0}
    >
      {#if clearing}<Spinner size="sm" />{/if}
      Clear All
    </button>
  </div>
</div>

<div class="page-body">
  {#if loading}
    <div class="flex items-center gap-3">
      <Spinner />
      <span class="text-muted">Loading…</span>
    </div>
  {:else if jobs.length === 0}
    <div class="card">
      <div class="empty-state">
        <div class="empty-icon">📭</div>
        <p>No job history yet. Start a scan to see results here.</p>
      </div>
    </div>
  {:else}
    <div class="card">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Status</th>
              <th>Device</th>
              <th>Target</th>
              <th>Profile</th>
              <th>Created</th>
              <th>Completed</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each jobs as job}
              <tr>
                <td class="font-mono" style="font-size:0.8rem">#{job.id}</td>
                <td>
                  <span class="badge {statusBadgeClass(job.status)}">{job.status}</span>
                </td>
                <td style="font-size:0.8rem">{job.device_name ?? job.device_id}</td>
                <td style="font-size:0.8rem">{job.target_name ?? job.target_id}</td>
                <td style="font-size:0.78rem;color:var(--color-text-muted)">{job.profile_id}</td>
                <td style="font-size:0.78rem;color:var(--color-text-muted);white-space:nowrap">{formatDate(job.created_at)}</td>
                <td style="font-size:0.78rem;color:var(--color-text-muted);white-space:nowrap">{formatDate(job.completed_at)}</td>
                <td>
                  <div class="action-btns">
                    {#if job.status === 'running' || job.status === 'queued'}
                      <button
                        class="btn btn-danger btn-sm"
                        onclick={() => handleCancel(job.id)}
                        disabled={cancellingIds.has(job.id)}
                      >
                        {#if cancellingIds.has(job.id)}<Spinner size="sm" />{/if}
                        Cancel
                      </button>
                    {/if}
                    {#if job.status === 'failed' && job.file_path}
                      <button
                        class="btn btn-secondary btn-sm"
                        onclick={() => handleRetry(job.id)}
                        disabled={retryingIds.has(job.id)}
                      >
                        {#if retryingIds.has(job.id)}<Spinner size="sm" />{/if}
                        Retry
                      </button>
                    {/if}
                    <button
                      class="btn btn-ghost btn-sm"
                      onclick={() => handleDelete(job.id)}
                      disabled={deletingIds.has(job.id)}
                    >
                      {#if deletingIds.has(job.id)}<Spinner size="sm" />{/if}
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
              {#if job.error}
                <tr class="error-row">
                  <td colspan="8">
                    <span class="text-error" style="font-size:0.78rem">Error: {job.error}</span>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>

<style>
  .action-btns {
    display: flex;
    gap: 4px;
    flex-wrap: nowrap;
  }

  .error-row td {
    padding-top: 0;
    padding-bottom: 8px;
    background: var(--color-error-dim);
  }
</style>
