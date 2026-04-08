<script lang="ts">
  import { onMount } from 'svelte';
  import { wsStore } from '$lib/stores/ws.svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import { listHistory, clearHistory, deleteHistoryItem, cancelHistoryJob, retryUpload } from '$lib/api/history';
  import type { Job } from '$lib/api/scan';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import { CheckCircle2, XCircle, Loader2, RotateCcw, X, Trash2, History, Clock } from 'lucide-svelte';

  let jobs = $state<Job[]>([]); let loading = $state(true); let clearing = $state(false);
  let cancellingIds = $state<Set<number>>(new Set());
  let retryingIds   = $state<Set<number>>(new Set());
  let deletingIds   = $state<Set<number>>(new Set());

  onMount(()=>load());

  $effect(()=>{
    const u=wsStore.lastJobUpdate; if(!u) return;
    const i=jobs.findIndex(j=>j.id===u.id);
    if(i!==-1) jobs=jobs.map(j=>j.id===u.id?u:j); else jobs=[u,...jobs];
  });

  async function load(){ loading=true; try{jobs=await listHistory();}catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}finally{loading=false;} }

  async function handleClear(){ if(!confirm('Clear all history?'))return; clearing=true; try{await clearHistory();jobs=[];showToast('Cleared','info');}catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}finally{clearing=false;} }

  async function handleCancel(id:number){ cancellingIds=new Set([...cancellingIds,id]); try{await cancelHistoryJob(id);jobs=jobs.map(j=>j.id===id?{...j,status:'cancelled' as Job['status']}:j);showToast('Cancelled','info');}catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}finally{cancellingIds.delete(id);cancellingIds=new Set(cancellingIds);} }

  async function handleRetry(id:number){ retryingIds=new Set([...retryingIds,id]); try{const u=await retryUpload(id);jobs=jobs.map(j=>j.id===id?u:j);showToast('Retry started','success');}catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}finally{retryingIds.delete(id);retryingIds=new Set(retryingIds);} }

  async function handleDelete(id:number){ deletingIds=new Set([...deletingIds,id]); try{await deleteHistoryItem(id);jobs=jobs.filter(j=>j.id!==id);showToast('Deleted','info');}catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}finally{deletingIds.delete(id);deletingIds=new Set(deletingIds);} }

  function sc(s:string){ return s==='completed'?'badge-success':s==='failed'?'badge-error':s==='running'?'badge-info':'badge-muted'; }

  function statusBorderColor(s:string){ return s==='completed'?'var(--c-ok)':s==='failed'?'var(--c-err)':s==='running'?'var(--c-accent)':'var(--c-border)'; }

  function fmtDate(ts:string|null){
    if(!ts) return '—';
    const d=new Date(ts); const diff=Math.floor((Date.now()-d.getTime())/1000);
    if(diff<60) return 'just now';
    if(diff<3600) return `${Math.floor(diff/60)}m ago`;
    if(diff<86400) return `${Math.floor(diff/3600)}h ago`;
    return d.toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'});
  }
</script>

<div class="page-wrap">
  <div class="page-header">
    <div><h1 class="page-title">History</h1><p class="page-sub">All scan jobs and their results</p></div>
    <button class="btn btn-secondary btn-sm" onclick={handleClear} disabled={clearing||!jobs.length}>
      {#if clearing}<Loader2 size={12} class="spin" />{:else}<Trash2 size={12} />{/if}
      Clear All
    </button>
  </div>

  {#if loading}
    <div style="display:flex;align-items:center;gap:10px;color:var(--c-text-2);padding:48px 0;"><Spinner /><span>Loading…</span></div>
  {:else if !jobs.length}
    <div class="card"><div class="empty-state"><History size={32} style="color:var(--c-surface-3);" /><p>No history yet.</p></div></div>
  {:else}
    <!-- Desktop table -->
    <div class="card show-desktop">
      <div class="table-wrap">
        <table>
          <thead><tr><th>Status</th><th>#</th><th>Device</th><th>Target</th><th>Profile</th><th>Created</th><th>Completed</th><th></th></tr></thead>
          <tbody>
            {#each jobs as job}
              <tr>
                <td>
                  <div style="display:flex;align-items:center;gap:6px;">
                    {#if job.status==='completed'}<CheckCircle2 size={13} style="color:var(--c-ok);" />
                    {:else if job.status==='failed'}<XCircle size={13} style="color:var(--c-err);" />
                    {:else if job.status==='running'}<span class="dot-pulse"></span>
                    {:else}<span class="dot-unknown"></span>{/if}
                    <span class="badge {sc(job.status)}">{job.status}</span>
                  </div>
                </td>
                <td style="font-family:var(--font-mono);font-size:0.75rem;color:var(--c-text-3);">#{job.id}</td>
                <td style="font-size:0.8125rem;">{job.device_name??job.device_id}</td>
                <td style="font-size:0.8125rem;">{job.target_name??job.target_id}</td>
                <td style="font-size:0.75rem;color:var(--c-text-2);">{job.profile_id}</td>
                <td style="font-size:0.75rem;color:var(--c-text-2);white-space:nowrap;">{fmtDate(job.created_at)}</td>
                <td style="font-size:0.75rem;color:var(--c-text-2);white-space:nowrap;">{fmtDate(job.completed_at)}</td>
                <td>
                  <div style="display:flex;gap:2px;">
                    {#if job.status==='running'||job.status==='queued'}
                      <button class="btn btn-ghost btn-icon btn-sm" onclick={()=>handleCancel(job.id)} disabled={cancellingIds.has(job.id)} title="Cancel">
                        {#if cancellingIds.has(job.id)}<Loader2 size={12} class="spin" />{:else}<X size={12} />{/if}
                      </button>
                    {/if}
                    {#if job.status==='failed'&&job.file_path}
                      <button class="btn btn-ghost btn-icon btn-sm" onclick={()=>handleRetry(job.id)} disabled={retryingIds.has(job.id)} title="Retry">
                        {#if retryingIds.has(job.id)}<Loader2 size={12} class="spin" />{:else}<RotateCcw size={12} />{/if}
                      </button>
                    {/if}
                    <button class="btn btn-ghost btn-icon btn-sm" onclick={()=>handleDelete(job.id)} disabled={deletingIds.has(job.id)} title="Delete">
                      {#if deletingIds.has(job.id)}<Loader2 size={12} class="spin" />{:else}<Trash2 size={12} />{/if}
                    </button>
                  </div>
                </td>
              </tr>
              {#if job.error}
                <tr><td colspan="8" style="padding-top:0;padding-bottom:8px;">
                  <div style="display:flex;align-items:center;gap:6px;font-size:0.75rem;color:var(--c-err);padding:5px 10px;background:rgba(239,68,68,0.06);border-radius:3px;">
                    <XCircle size={11} />{job.error}
                  </div>
                </td></tr>
              {/if}
            {/each}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Mobile list -->
    <div class="mobile-list" style="display:flex;flex-direction:column;gap:8px;">
      {#each jobs as job}
        <div class="card" style="border-left:2px solid {statusBorderColor(job.status)};">
          <div style="padding:12px;">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:6px;">
              <div style="display:flex;align-items:center;gap:7px;">
                {#if job.status==='completed'}<CheckCircle2 size={14} style="color:var(--c-ok);flex-shrink:0;" />
                {:else if job.status==='failed'}<XCircle size={14} style="color:var(--c-err);flex-shrink:0;" />
                {:else if job.status==='running'}<span class="dot-pulse" style="flex-shrink:0;"></span>
                {:else}<Clock size={13} style="color:var(--c-text-3);flex-shrink:0;" />{/if}
                <p style="font-size:0.875rem;font-weight:500;color:var(--c-text);">{job.filename_prefix??'scan'}_{job.id}</p>
              </div>
              <span style="font-size:0.75rem;color:var(--c-text-3);flex-shrink:0;">{fmtDate(job.created_at)}</span>
            </div>

            <p style="font-size:0.75rem;color:var(--c-text-2);margin-bottom:8px;">{job.device_name??job.device_id} → {job.target_name??job.target_id} · {job.profile_id}</p>

            {#if job.error}
              <p style="font-size:0.75rem;color:var(--c-err);padding:5px 8px;background:rgba(239,68,68,0.07);border-radius:3px;margin-bottom:8px;">{job.error}</p>
            {/if}

            <div style="display:flex;align-items:center;gap:6px;">
              <span class="badge {sc(job.status)}">{job.status}</span>
              <div style="display:flex;gap:4px;margin-left:auto;">
                {#if job.status==='running'||job.status==='queued'}
                  <button class="btn btn-ghost btn-sm" onclick={()=>handleCancel(job.id)} disabled={cancellingIds.has(job.id)}><X size={12} />Cancel</button>
                {/if}
                {#if job.status==='failed'&&job.file_path}
                  <button class="btn btn-ghost btn-sm" onclick={()=>handleRetry(job.id)} disabled={retryingIds.has(job.id)}><RotateCcw size={12} />Retry</button>
                {/if}
                <button class="btn btn-ghost btn-icon btn-sm" onclick={()=>handleDelete(job.id)} disabled={deletingIds.has(job.id)} style="color:var(--c-text-3);">
                  <Trash2 size={12} />
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
  :global(.spin){animation:spin .7s linear infinite;}
  @keyframes spin{to{transform:rotate(360deg);}}

  /* Show table on desktop, list on mobile */
  .show-desktop { display: block !important; }
  .mobile-list  { display: none !important; }

  @media (max-width: 768px) {
    .show-desktop { display: none !important; }
    .mobile-list  { display: flex !important; }
  }
</style>
