<script lang="ts">
  import { onMount } from 'svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import { listTargets, createTarget, updateTarget, deleteTarget, testTarget, setTargetFavorite, type Target, type TargetIn } from '$lib/api/targets';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import Modal from '$lib/components/ui/Modal.svelte';
  import TargetForm from '$lib/components/domain/TargetForm.svelte';
  import { Plus, Pencil, Trash2, Star, StarOff, CheckCircle2, XCircle, Loader2, FlaskConical, Crosshair } from 'lucide-svelte';

  let targets = $state<Target[]>([]); let loading = $state(true);
  let showFormModal = $state(false); let editTarget = $state<Target|null>(null);
  let testingIds  = $state<Set<string>>(new Set()); let deletingIds  = $state<Set<string>>(new Set());
  let favoriteIds = $state<Set<string>>(new Set());
  let testResults = $state<Map<string,{success:boolean;message:string}>>(new Map());
  const st = $derived([...targets].sort((a,b)=>Number(b.is_favorite)-Number(a.is_favorite)));

  onMount(()=>load());

  async function load(){ loading=true; try{targets=await listTargets();}catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}finally{loading=false;} }

  async function handleSave(data: TargetIn){
    try{
      if(editTarget){const u=await updateTarget(editTarget.id,data);targets=targets.map(t=>t.id===u.id?u:t);showToast('Updated','success');}
      else{const c=await createTarget(data);targets=[...targets,c];showToast('Created','success');}
      showFormModal=false;
    }catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');throw e;}
  }

  async function handleDelete(t: Target){
    if(!confirm(`Delete "${t.name}"?`))return;
    deletingIds=new Set([...deletingIds,t.id]);
    try{await deleteTarget(t.id);targets=targets.filter(x=>x.id!==t.id);testResults.delete(t.id);showToast('Deleted','info');}
    catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}
    finally{deletingIds.delete(t.id);deletingIds=new Set(deletingIds);}
  }

  async function handleTest(t: Target){
    testingIds=new Set([...testingIds,t.id]);testResults.delete(t.id);testResults=new Map(testResults);
    try{const r=await testTarget(t.id);testResults=new Map([...testResults,[t.id,r]]);showToast(`${t.name}: ${r.message}`,r.success?'success':'error');}
    catch(e:unknown){const m=e instanceof Error?e.message:'Failed';testResults=new Map([...testResults,[t.id,{success:false,message:m}]]);showToast(m,'error');}
    finally{testingIds.delete(t.id);testingIds=new Set(testingIds);}
  }

  async function handleFav(t: Target){
    favoriteIds=new Set([...favoriteIds,t.id]);
    try{await setTargetFavorite(t.id,!t.is_favorite);targets=targets.map(x=>x.id===t.id?{...x,is_favorite:!x.is_favorite}:x);}
    catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}
    finally{favoriteIds.delete(t.id);favoriteIds=new Set(favoriteIds);}
  }

  const TYPE_COLOR: Record<string,string> = {
    smb:'#60a5fa',sftp:'#a78bfa',email:'#fb923c',paperless:'#4ade80',
    webhook:'#f472b6',google_drive:'#facc15',dropbox:'#38bdf8',onedrive:'#818cf8',nextcloud:'#f87171'
  };
  const TYPE_LABEL: Record<string,string> = {
    smb:'SMB',sftp:'SFTP',email:'Email',paperless:'Paperless',
    webhook:'Webhook',google_drive:'Google Drive',dropbox:'Dropbox',onedrive:'OneDrive',nextcloud:'Nextcloud'
  };
  function tc(type:string){ return TYPE_COLOR[type]??'#888'; }
  function tl(type:string){ return TYPE_LABEL[type]??type; }
</script>

<div class="page-wrap">
  <div class="page-header">
    <div><h1 class="page-title">Targets</h1><p class="page-sub">Delivery destinations for scanned documents</p></div>
    <button class="btn btn-primary" onclick={()=>{editTarget=null;showFormModal=true;}}><Plus size={14} />Add Target</button>
  </div>

  {#if loading}
    <div style="display:flex;align-items:center;gap:10px;color:var(--c-text-2);padding:48px 0;"><Spinner /><span>Loading…</span></div>
  {:else if !st.length}
    <div class="card"><div class="empty-state"><Crosshair size={32} style="color:var(--c-surface-3);" /><p>No targets yet. Add a delivery destination!</p></div></div>
  {:else}
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:12px;">
      {#each st as t}
        <div class="card" style="display:flex;flex-direction:column;">
          <!-- Body -->
          <div style="padding:14px;flex:1;">
            <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:10px;">
              <!-- Type color block -->
              <div style="width:32px;height:32px;border-radius:5px;background:{tc(t.type)}1a;border:1px solid {tc(t.type)}33;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                <Crosshair size={15} style="color:{tc(t.type)};" />
              </div>
              <div style="min-width:0;flex:1;">
                <div style="display:flex;align-items:center;gap:5px;">
                  <p style="font-size:0.875rem;font-weight:600;color:var(--c-text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{t.name}</p>
                  {#if t.is_favorite}<Star size={11} style="color:#fbbf24;flex-shrink:0;" fill="currentColor" />{/if}
                </div>
                <span style="display:inline-block;font-size:0.6875rem;font-weight:600;padding:1px 6px;border-radius:3px;border:1px solid {tc(t.type)}33;background:{tc(t.type)}1a;color:{tc(t.type)};">{tl(t.type)}</span>
              </div>
            </div>

            {#if (t.config?.connection as string) || (t.config?.host as string)}
              <p style="font-size:0.75rem;font-family:var(--font-mono);color:var(--c-text-3);background:var(--c-surface-2);border:1px solid var(--c-border);border-radius:4px;padding:5px 8px;margin-bottom:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{(t.config?.connection as string) || (t.config?.host as string)}</p>
            {/if}
            {#if t.config?.username}
              <p style="font-size:0.75rem;color:var(--c-text-2);">👤 {t.config.username as string}</p>
            {/if}

            {#if testResults.has(t.id)}
              {@const r=testResults.get(t.id)!}
              <div style="display:flex;align-items:center;gap:6px;font-size:0.75rem;padding:7px 8px;border-radius:4px;margin-top:8px;{r.success?'background:rgba(34,197,94,0.08);color:#4ade80;':'background:rgba(239,68,68,0.08);color:#f87171;'}">
                {#if r.success}<CheckCircle2 size={12} />{:else}<XCircle size={12} />{/if}
                {r.message}
              </div>
            {/if}
          </div>

          <!-- Actions -->
          <div style="display:flex;align-items:center;gap:4px;padding:10px 14px;border-top:1px solid var(--c-border);">
            <button class="btn btn-ghost btn-icon btn-sm" onclick={()=>handleFav(t)} disabled={favoriteIds.has(t.id)} title={t.is_favorite?'Unfavorite':'Favorite'}>
              {#if t.is_favorite}<Star size={13} fill="currentColor" style="color:#fbbf24;" />{:else}<StarOff size={13} />{/if}
            </button>
            <button class="btn btn-secondary btn-sm" onclick={()=>handleTest(t)} disabled={testingIds.has(t.id)}>
              {#if testingIds.has(t.id)}<Loader2 size={12} class="spin" />{:else}<FlaskConical size={12} />{/if}
              Test
            </button>
            <button class="btn btn-ghost btn-sm" onclick={()=>{editTarget=t;showFormModal=true;}}><Pencil size={12} />Edit</button>
            <button class="btn btn-ghost btn-sm" style="margin-left:auto;color:var(--c-text-3);" onclick={()=>handleDelete(t)} disabled={deletingIds.has(t.id)}>
              {#if deletingIds.has(t.id)}<Loader2 size={12} class="spin" />{:else}<Trash2 size={12} />{/if}
            </button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<Modal open={showFormModal} title={editTarget?`Edit: ${editTarget.name}`:'Add Target'} onClose={()=>(showFormModal=false)} wide>
  <TargetForm target={editTarget} onSave={handleSave} onCancel={()=>(showFormModal=false)} />
</Modal>

<style>
  :global(.spin){animation:spin .7s linear infinite;}
  @keyframes spin{to{transform:rotate(360deg);}}
</style>
