<script lang="ts">
  import { onMount } from 'svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import {
    listTargets, createTarget, updateTarget, deleteTarget,
    testTarget, setTargetFavorite, type Target, type TargetIn
  } from '$lib/api/targets';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import Modal from '$lib/components/ui/Modal.svelte';
  import TargetForm from '$lib/components/domain/TargetForm.svelte';
  import { Plus, Pencil, Trash2, Star, StarOff, CheckCircle2, XCircle, Loader2,
           FlaskConical, Crosshair } from 'lucide-svelte';

  let targets       = $state<Target[]>([]);
  let loading       = $state(true);
  let showFormModal = $state(false);
  let editTarget    = $state<Target | null>(null);

  let testingIds   = $state<Set<number>>(new Set());
  let deletingIds  = $state<Set<number>>(new Set());
  let favoriteIds  = $state<Set<number>>(new Set());
  let testResults  = $state<Map<number, { success: boolean; message: string }>>(new Map());

  const sortedTargets = $derived([...targets].sort((a,b) => Number(b.is_favorite)-Number(a.is_favorite)));

  onMount(() => loadTargets());

  async function loadTargets() {
    loading = true;
    try { targets = await listTargets(); }
    catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Failed', 'error'); }
    finally { loading = false; }
  }

  function openAdd()     { editTarget = null; showFormModal = true; }
  function openEdit(t: Target) { editTarget = t; showFormModal = true; }

  async function handleSave(data: TargetIn) {
    try {
      if (editTarget) {
        const updated = await updateTarget(editTarget.id, data);
        targets = targets.map(t => t.id === updated.id ? updated : t);
        showToast('Target updated', 'success');
      } else {
        const created = await createTarget(data);
        targets = [...targets, created];
        showToast('Target created', 'success');
      }
      showFormModal = false;
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Save failed', 'error'); throw err; }
  }

  async function handleDelete(t: Target) {
    if (!confirm(`Delete target "${t.name}"?`)) return;
    deletingIds = new Set([...deletingIds, t.id]);
    try {
      await deleteTarget(t.id);
      targets = targets.filter(x => x.id !== t.id);
      testResults.delete(t.id);
      showToast('Target deleted', 'info');
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Failed', 'error'); }
    finally { deletingIds.delete(t.id); deletingIds = new Set(deletingIds); }
  }

  async function handleTest(t: Target) {
    testingIds = new Set([...testingIds, t.id]);
    testResults.delete(t.id); testResults = new Map(testResults);
    try {
      const result = await testTarget(t.id);
      testResults = new Map([...testResults, [t.id, result]]);
      showToast(`${t.name}: ${result.message}`, result.success ? 'success' : 'error');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Test failed';
      testResults = new Map([...testResults, [t.id, { success: false, message: msg }]]);
      showToast(msg, 'error');
    } finally { testingIds.delete(t.id); testingIds = new Set(testingIds); }
  }

  async function handleFavorite(t: Target) {
    favoriteIds = new Set([...favoriteIds, t.id]);
    try {
      await setTargetFavorite(t.id, !t.is_favorite);
      targets = targets.map(x => x.id === t.id ? { ...x, is_favorite: !x.is_favorite } : x);
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Failed', 'error'); }
    finally { favoriteIds.delete(t.id); favoriteIds = new Set(favoriteIds); }
  }

  // Type metadata
  const TYPE_META: Record<string, { label: string; color: string; bg: string }> = {
    smb:          { label: 'SMB',          color: '#60a5fa', bg: 'rgba(96,165,250,0.1)' },
    sftp:         { label: 'SFTP',         color: '#a78bfa', bg: 'rgba(167,139,250,0.1)' },
    email:        { label: 'Email',        color: '#fb923c', bg: 'rgba(251,146,60,0.1)' },
    paperless:    { label: 'Paperless',    color: '#4ade80', bg: 'rgba(74,222,128,0.1)' },
    webhook:      { label: 'Webhook',      color: '#f472b6', bg: 'rgba(244,114,182,0.1)' },
    google_drive: { label: 'Google Drive', color: '#facc15', bg: 'rgba(250,204,21,0.1)' },
    dropbox:      { label: 'Dropbox',      color: '#38bdf8', bg: 'rgba(56,189,248,0.1)' },
    onedrive:     { label: 'OneDrive',     color: '#818cf8', bg: 'rgba(129,140,248,0.1)' },
    nextcloud:    { label: 'Nextcloud',    color: '#f87171', bg: 'rgba(248,113,113,0.1)' },
  };

  function typeMeta(type: string) {
    return TYPE_META[type] ?? { label: type, color: '#9ca3af', bg: 'rgba(156,163,175,0.1)' };
  }
</script>

<div class="page-wrap">
  <!-- Header -->
  <div class="page-header">
    <div>
      <h1 class="page-title">Targets</h1>
      <p class="page-sub">Delivery destinations for scanned documents</p>
    </div>
    <button class="btn btn-primary" onclick={openAdd}>
      <Plus size={15} /> Add Target
    </button>
  </div>

  {#if loading}
    <div class="flex items-center gap-3 text-zinc-500 py-12"><Spinner /><span>Loading…</span></div>
  {:else if sortedTargets.length === 0}
    <div class="card">
      <div class="empty-state">
        <Crosshair size={40} class="text-zinc-800" />
        <p>No targets yet.<br />Add your first delivery destination!</p>
      </div>
    </div>
  {:else}
    <div class="grid gap-4" style="grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));">
      {#each sortedTargets as t}
        {@const meta = typeMeta(t.type)}
        <div class="card flex flex-col overflow-hidden">

          <!-- Card body -->
          <div class="p-4 flex-1">
            <div class="flex items-start justify-between gap-2 mb-3">
              <div class="flex items-center gap-2.5 min-w-0">
                <!-- Type badge -->
                <div class="rounded-lg flex items-center justify-center flex-shrink-0"
                     style="width:34px;height:34px;background:{meta.bg};color:{meta.color};">
                  <Crosshair size={16} />
                </div>
                <div class="min-w-0">
                  <div class="flex items-center gap-1.5">
                    <p class="font-semibold text-zinc-100 text-sm truncate">{t.name}</p>
                    {#if t.is_favorite}
                      <Star size={12} class="text-amber-400 flex-shrink-0" fill="currentColor" />
                    {/if}
                  </div>
                  <span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium"
                        style="background:{meta.bg};color:{meta.color};">{meta.label}</span>
                </div>
              </div>
            </div>

            {#if t.connection}
              <p class="text-xs font-mono text-zinc-500 bg-zinc-950/50 rounded px-2 py-1 mb-2 truncate">{t.connection}</p>
            {/if}
            {#if t.username}
              <p class="text-xs text-zinc-500 mb-2">👤 {t.username}</p>
            {/if}

            {#if testResults.has(t.id)}
              {@const r = testResults.get(t.id)!}
              <div class="flex items-center gap-1.5 text-xs rounded-lg p-2 mt-2"
                   style="{r.success ? 'background:rgba(74,222,128,0.1);color:#4ade80;' : 'background:rgba(248,113,113,0.1);color:#f87171;'}">
                {#if r.success}
                  <CheckCircle2 size={13} />
                {:else}
                  <XCircle size={13} />
                {/if}
                {r.message}
              </div>
            {/if}
          </div>

          <!-- Actions footer -->
          <div class="flex items-center gap-1 px-4 py-3 border-t border-zinc-800/60 bg-zinc-950/30">
            <button class="btn btn-ghost btn-icon btn-sm" title={t.is_favorite ? 'Unfavorite' : 'Favorite'}
                    onclick={() => handleFavorite(t)} disabled={favoriteIds.has(t.id)}>
              {#if t.is_favorite}
                <Star size={14} fill="currentColor" class="text-amber-400" />
              {:else}
                <StarOff size={14} />
              {/if}
            </button>
            <button class="btn btn-secondary btn-sm" onclick={() => handleTest(t)} disabled={testingIds.has(t.id)}>
              {#if testingIds.has(t.id)}<Loader2 size={13} class="animate-spin" />{:else}<FlaskConical size={13} />{/if}
              Test
            </button>
            <button class="btn btn-ghost btn-sm" onclick={() => openEdit(t)}>
              <Pencil size={13} /> Edit
            </button>
            <button class="btn btn-ghost btn-sm hover:text-red-400 ml-auto"
                    onclick={() => handleDelete(t)} disabled={deletingIds.has(t.id)}>
              {#if deletingIds.has(t.id)}<Loader2 size={13} class="animate-spin" />{:else}<Trash2 size={13} />{/if}
              Delete
            </button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<Modal open={showFormModal} title={editTarget ? `Edit: ${editTarget.name}` : 'Add Target'}
       onClose={() => (showFormModal = false)} wide>
  <TargetForm target={editTarget} onSave={handleSave} onCancel={() => (showFormModal = false)} />
</Modal>

<style>
  :global(.animate-spin) { animation: spin 0.75s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
