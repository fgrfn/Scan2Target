<script lang="ts">
  import { onMount } from 'svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import {
    listTargets,
    createTarget,
    updateTarget,
    deleteTarget,
    testTarget,
    setTargetFavorite,
    type Target,
    type TargetIn
  } from '$lib/api/targets';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import Modal from '$lib/components/ui/Modal.svelte';
  import TargetForm from '$lib/components/domain/TargetForm.svelte';

  let targets = $state<Target[]>([]);
  let loading = $state(true);
  let showFormModal = $state(false);
  let editTarget = $state<Target | null>(null);

  // Per-target operation state
  let testingIds = $state<Set<number>>(new Set());
  let deletingIds = $state<Set<number>>(new Set());
  let favoriteIds = $state<Set<number>>(new Set());
  let testResults = $state<Map<number, { success: boolean; message: string }>>(new Map());

  onMount(async () => {
    await loadTargets();
  });

  async function loadTargets() {
    loading = true;
    try {
      targets = await listTargets();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load targets', 'error');
    } finally {
      loading = false;
    }
  }

  function openAdd() {
    editTarget = null;
    showFormModal = true;
  }

  function openEdit(t: Target) {
    editTarget = t;
    showFormModal = true;
  }

  async function handleSave(data: TargetIn) {
    try {
      if (editTarget) {
        const updated = await updateTarget(editTarget.id, data);
        targets = targets.map((t) => (t.id === updated.id ? updated : t));
        showToast('Target updated', 'success');
      } else {
        const created = await createTarget(data);
        targets = [...targets, created];
        showToast('Target created', 'success');
      }
      showFormModal = false;
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Save failed', 'error');
      throw err; // let form handle loading state
    }
  }

  async function handleDelete(t: Target) {
    if (!confirm(`Delete target "${t.name}"?`)) return;
    deletingIds = new Set([...deletingIds, t.id]);
    try {
      await deleteTarget(t.id);
      targets = targets.filter((x) => x.id !== t.id);
      testResults.delete(t.id);
      showToast('Target deleted', 'info');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Delete failed', 'error');
    } finally {
      deletingIds.delete(t.id);
      deletingIds = new Set(deletingIds);
    }
  }

  async function handleTest(t: Target) {
    testingIds = new Set([...testingIds, t.id]);
    testResults.delete(t.id);
    testResults = new Map(testResults);
    try {
      const result = await testTarget(t.id);
      testResults = new Map([...testResults, [t.id, result]]);
      showToast(
        `${t.name}: ${result.message}`,
        result.success ? 'success' : 'error'
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Test failed';
      testResults = new Map([...testResults, [t.id, { success: false, message: msg }]]);
      showToast(msg, 'error');
    } finally {
      testingIds.delete(t.id);
      testingIds = new Set(testingIds);
    }
  }

  async function handleFavorite(t: Target) {
    favoriteIds = new Set([...favoriteIds, t.id]);
    try {
      await setTargetFavorite(t.id, !t.is_favorite);
      targets = targets.map((x) =>
        x.id === t.id ? { ...x, is_favorite: !x.is_favorite } : x
      );
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed', 'error');
    } finally {
      favoriteIds.delete(t.id);
      favoriteIds = new Set(favoriteIds);
    }
  }

  const sortedTargets = $derived(
    [...targets].sort((a, b) => Number(b.is_favorite) - Number(a.is_favorite))
  );

  const TYPE_LABELS: Record<string, string> = {
    smb: 'SMB',
    sftp: 'SFTP',
    email: 'Email',
    paperless: 'Paperless',
    webhook: 'Webhook',
    google_drive: 'Google Drive',
    dropbox: 'Dropbox',
    onedrive: 'OneDrive',
    nextcloud: 'Nextcloud'
  };

  const TYPE_ICONS: Record<string, string> = {
    smb: '🗂',
    sftp: '🖥',
    email: '📧',
    paperless: '📄',
    webhook: '🔗',
    google_drive: '☁',
    dropbox: '📦',
    onedrive: '☁',
    nextcloud: '🌩'
  };
</script>

<div class="page-header">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="page-title">🎯 Targets</h1>
      <p class="page-subtitle">Configure delivery destinations for scanned documents</p>
    </div>
    <button class="btn btn-primary" onclick={openAdd}>+ Add Target</button>
  </div>
</div>

<div class="page-body">
  {#if loading}
    <div class="flex items-center gap-3">
      <Spinner />
      <span class="text-muted">Loading…</span>
    </div>
  {:else if sortedTargets.length === 0}
    <div class="card">
      <div class="empty-state">
        <div class="empty-icon">🎯</div>
        <p>No targets yet. Add your first delivery destination!</p>
      </div>
    </div>
  {:else}
    <div class="targets-grid">
      {#each sortedTargets as t}
        <div class="card target-card">
          <div class="target-header">
            <div class="target-identity">
              <span class="type-icon">{TYPE_ICONS[t.type] ?? '📁'}</span>
              <div>
                <div class="target-name">
                  {t.name}
                  {#if t.is_favorite}<span title="Favorite" style="color:var(--color-warning)">★</span>{/if}
                </div>
                <span class="badge badge-primary" style="margin-top:2px">{TYPE_LABELS[t.type] ?? t.type}</span>
              </div>
            </div>
          </div>

          {#if t.connection}
            <div class="target-conn font-mono">{t.connection}</div>
          {/if}
          {#if t.username}
            <div class="target-user">👤 {t.username}</div>
          {/if}

          {#if testResults.has(t.id)}
            {@const result = testResults.get(t.id)!}
            <div class="test-result" class:success={result.success} class:fail={!result.success}>
              {result.success ? '✓' : '✕'} {result.message}
            </div>
          {/if}

          <div class="target-actions">
            <button
              class="btn btn-ghost btn-icon btn-sm"
              title={t.is_favorite ? 'Unfavorite' : 'Favorite'}
              onclick={() => handleFavorite(t)}
              disabled={favoriteIds.has(t.id)}
            >
              {t.is_favorite ? '★' : '☆'}
            </button>
            <button
              class="btn btn-secondary btn-sm"
              onclick={() => handleTest(t)}
              disabled={testingIds.has(t.id)}
            >
              {#if testingIds.has(t.id)}<Spinner size="sm" />{/if}
              Test
            </button>
            <button class="btn btn-ghost btn-sm" onclick={() => openEdit(t)}>
              Edit
            </button>
            <button
              class="btn btn-danger btn-sm"
              onclick={() => handleDelete(t)}
              disabled={deletingIds.has(t.id)}
            >
              {#if deletingIds.has(t.id)}<Spinner size="sm" />{/if}
              Delete
            </button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<Modal
  open={showFormModal}
  title={editTarget ? `Edit: ${editTarget.name}` : 'Add Target'}
  onClose={() => (showFormModal = false)}
  wide={true}
>
  <TargetForm target={editTarget} onSave={handleSave} onCancel={() => (showFormModal = false)} />
</Modal>

<style>
  .targets-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
  }

  .target-card {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .target-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
  }

  .target-identity {
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }

  .type-icon {
    font-size: 1.6rem;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .target-name {
    font-weight: 600;
    font-size: 0.95rem;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .target-conn {
    font-size: 0.78rem;
    color: var(--color-text-dim);
    word-break: break-all;
    background: var(--color-bg);
    padding: 6px 10px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border-subtle);
  }

  .target-user {
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }

  .test-result {
    font-size: 0.8rem;
    padding: 8px 10px;
    border-radius: var(--radius-sm);
    border: 1px solid transparent;
  }

  .test-result.success {
    background: var(--color-success-dim);
    color: var(--color-success);
    border-color: var(--color-success);
  }

  .test-result.fail {
    background: var(--color-error-dim);
    color: var(--color-error);
    border-color: var(--color-error);
  }

  .target-actions {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    align-items: center;
    padding-top: 6px;
    border-top: 1px solid var(--color-border-subtle);
    margin-top: auto;
  }
</style>
