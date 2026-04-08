<script lang="ts">
  import { onMount } from 'svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import { wsStore } from '$lib/stores/ws.svelte';
  import { listDevices, discoverDevices, addDevice, removeDevice, setDeviceFavorite, checkDeviceOnline, type Device, type DiscoveredDevice } from '$lib/api/devices';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import Modal from '$lib/components/ui/Modal.svelte';
  import { Printer, Plus, Search, RefreshCw, Trash2, Star, StarOff, Clock, Loader2 } from 'lucide-svelte';

  let devices = $state<Device[]>([]); let discovered = $state<DiscoveredDevice[]>([]);
  let loading = $state(true); let discovering = $state(false);
  let showDiscoverModal = $state(false); let showAddModal = $state(false);
  let addUri = $state(''); let addName = $state(''); let addModel = $state(''); let addManufacturer = $state(''); let addLoading = $state(false);
  let checkingIds = $state<Set<string>>(new Set()); let removingIds = $state<Set<string>>(new Set()); let favoriteIds = $state<Set<string>>(new Set());

  const sd = $derived([...devices].sort((a,b)=>Number(b.is_favorite)-Number(a.is_favorite)));
  const nd = $derived(discovered.filter(d=>!devices.some(x=>x.uri===d.uri)));

  onMount(()=>loadDevices());

  $effect(()=>{ const u=wsStore.lastScannerUpdate; if(!u) return; devices=devices.map(d=>d.uri===u.uri?{...d,online:u.online,name:u.name||d.name}:d); });

  async function loadDevices() { loading=true; try{devices=await listDevices();}catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}finally{loading=false;} }

  async function handleDiscover() { discovering=true; try{discovered=await discoverDevices();showDiscoverModal=true;}catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}finally{discovering=false;} }

  async function handleAddDiscovered(d: DiscoveredDevice) {
    try{const c=await addDevice({uri:d.uri,name:d.name,model:d.model??undefined,make:d.make??undefined});devices=[...devices,c];discovered=discovered.filter(x=>x.uri!==d.uri);showToast(`Added ${c.name}`,'success');if(!discovered.filter(x=>!devices.some(y=>y.uri===x.uri)).length)showDiscoverModal=false;}
    catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}
  }

  async function handleAddManual(e: SubmitEvent) {
    e.preventDefault();addLoading=true;
    try{const c=await addDevice({uri:addUri,name:addName,model:addModel||undefined,make:addManufacturer||undefined});devices=[...devices,c];showAddModal=false;addUri='';addName='';addModel='';addManufacturer='';showToast(`Added ${c.name}`,'success');}
    catch(ex:unknown){showToast(ex instanceof Error?ex.message:'Failed','error');}finally{addLoading=false;}
  }

  async function handleRemove(id: string) {
    if(!confirm('Remove this scanner?'))return;
    removingIds=new Set([...removingIds,id]);
    try{await removeDevice(id);devices=devices.filter(d=>d.id!==id);showToast('Removed','info');}
    catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}
    finally{removingIds.delete(id);removingIds=new Set(removingIds);}
  }

  async function handleFavorite(d: Device) {
    favoriteIds=new Set([...favoriteIds,d.id]);
    try{await setDeviceFavorite(d.id,!d.is_favorite);devices=devices.map(x=>x.id===d.id?{...x,is_favorite:!x.is_favorite}:x);}
    catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}
    finally{favoriteIds.delete(d.id);favoriteIds=new Set(favoriteIds);}
  }

  async function handleCheck(d: Device) {
    checkingIds=new Set([...checkingIds,d.id]);
    try{const r=await checkDeviceOnline(d.id);devices=devices.map(x=>x.id===d.id?{...x,online:r.online,last_seen:new Date().toISOString()}:x);showToast(`${d.name}: ${r.online?'Online':'Offline'}`,r.online?'success':'info');}
    catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}
    finally{checkingIds.delete(d.id);checkingIds=new Set(checkingIds);}
  }

  function fmtDate(ts: string|null) {
    if(!ts) return 'Never';
    const diff=Math.floor((Date.now()-new Date(ts).getTime())/1000);
    if(diff<60) return 'just now';
    if(diff<3600) return `${Math.floor(diff/60)}m ago`;
    if(diff<86400) return `${Math.floor(diff/3600)}h ago`;
    return new Date(ts).toLocaleDateString();
  }
</script>

<div class="page-wrap">
  <div class="page-header">
    <div><h1 class="page-title">Devices</h1><p class="page-sub">Manage your network scanners</p></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <button class="btn btn-secondary" onclick={handleDiscover} disabled={discovering}>
        {#if discovering}<Loader2 size={14} class="spin" />{:else}<Search size={14} />{/if}
        Discover
      </button>
      <button class="btn btn-primary" onclick={()=>(showAddModal=true)}><Plus size={14} />Add Scanner</button>
    </div>
  </div>

  {#if loading}
    <div style="display:flex;align-items:center;gap:10px;color:var(--c-text-2);padding:48px 0;"><Spinner /><span>Loading…</span></div>
  {:else if !sd.length}
    <div class="card"><div class="empty-state"><Printer size={32} style="color:var(--c-surface-3);" /><p>No scanners yet. Click <strong>Discover</strong> or <strong>Add Scanner</strong>.</p></div></div>
  {:else}
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:12px;">
      {#each sd as d}
        <div class="card">
          <!-- Header -->
          <div style="display:flex;align-items:flex-start;justify-content:space-between;padding:14px 14px 0;">
            <div style="display:flex;align-items:center;gap:8px;min-width:0;">
              <span class="{d.online===true?'dot-online':d.online===false?'dot-offline':'dot-unknown'}"></span>
              <div style="min-width:0;">
                <p style="font-size:0.875rem;font-weight:600;color:var(--c-text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{d.name}</p>
                {#if d.make||d.model}
                  <p style="font-size:0.75rem;color:var(--c-text-2);">{[d.make,d.model].filter(Boolean).join(' ')}</p>
                {/if}
              </div>
              {#if d.is_favorite}<Star size={12} style="color:#fbbf24;flex-shrink:0;" fill="currentColor" />{/if}
            </div>
            <div style="display:flex;gap:2px;flex-shrink:0;">
              <button class="btn btn-ghost btn-icon btn-sm" onclick={()=>handleFavorite(d)} disabled={favoriteIds.has(d.id)} title={d.is_favorite?'Unfavorite':'Favorite'}>
                {#if d.is_favorite}<Star size={13} fill="currentColor" style="color:#fbbf24;" />{:else}<StarOff size={13} />{/if}
              </button>
              <button class="btn btn-ghost btn-icon btn-sm" onclick={()=>handleCheck(d)} disabled={checkingIds.has(d.id)} title="Check">
                {#if checkingIds.has(d.id)}<Loader2 size={13} class="spin" />{:else}<RefreshCw size={13} />{/if}
              </button>
              <button class="btn btn-ghost btn-icon btn-sm" onclick={()=>handleRemove(d.id)} disabled={removingIds.has(d.id)} title="Remove" style="color:var(--c-text-3);">
                <Trash2 size={13} />
              </button>
            </div>
          </div>
          <!-- Details -->
          <div style="margin:10px 14px 14px;padding:10px;background:var(--c-surface-2);border:1px solid var(--c-border);border-radius:5px;display:flex;flex-direction:column;gap:5px;">
            <div style="display:flex;gap:8px;align-items:flex-start;">
              <span style="font-size:0.6875rem;color:var(--c-text-3);width:48px;flex-shrink:0;padding-top:1px;">URI</span>
              <span style="font-size:0.75rem;color:var(--c-text-2);font-family:var(--font-mono);word-break:break-all;">{d.uri}</span>
            </div>
            <div style="display:flex;align-items:center;gap:5px;">
              <Clock size={10} style="color:var(--c-text-3);" />
              <span style="font-size:0.75rem;color:var(--c-text-3);">{fmtDate(d.last_seen)}</span>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<Modal open={showDiscoverModal} title="Discovered Scanners" onClose={()=>(showDiscoverModal=false)} wide>
  {#if !nd.length}
    <div class="empty-state" style="padding:24px;"><Search size={28} style="color:var(--c-surface-3);" /><p>No new scanners found.</p></div>
  {:else}
    <p style="font-size:0.8125rem;color:var(--c-text-2);margin-bottom:12px;">{nd.length} found</p>
    <div style="display:flex;flex-direction:column;gap:8px;">
      {#each nd as d}
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px;background:var(--c-surface-2);border:1px solid var(--c-border);border-radius:6px;">
          <div style="display:flex;align-items:center;gap:10px;min-width:0;">
            <Printer size={16} style="color:var(--c-text-2);flex-shrink:0;" />
            <div style="min-width:0;">
              <p style="font-weight:500;font-size:0.875rem;color:var(--c-text);">{d.name}</p>
              <p style="font-size:0.75rem;color:var(--c-text-3);font-family:var(--font-mono);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{d.uri}</p>
            </div>
          </div>
          <button class="btn btn-primary btn-sm" onclick={()=>handleAddDiscovered(d)}>Add</button>
        </div>
      {/each}
    </div>
  {/if}
</Modal>

<Modal open={showAddModal} title="Add Scanner Manually" onClose={()=>(showAddModal=false)}>
  <form onsubmit={handleAddManual} style="display:flex;flex-direction:column;gap:14px;">
    <div class="form-group">
      <label class="form-label" for="au">Scanner URI</label>
      <input id="au" class="form-control" type="text" bind:value={addUri} placeholder="escl://192.168.1.100:443/eSCL" required />
      <span class="form-hint">SANE URI or eSCL URL.</span>
    </div>
    <div class="form-group">
      <label class="form-label" for="an">Display Name</label>
      <input id="an" class="form-control" type="text" bind:value={addName} placeholder="Office Scanner" required />
    </div>
    <div class="form-row">
      <div class="form-group">
        <label class="form-label" for="am">Manufacturer</label>
        <input id="am" class="form-control" type="text" bind:value={addManufacturer} placeholder="HP" />
      </div>
      <div class="form-group">
        <label class="form-label" for="amd">Model</label>
        <input id="amd" class="form-control" type="text" bind:value={addModel} placeholder="LaserJet" />
      </div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button type="button" class="btn btn-secondary" onclick={()=>(showAddModal=false)}>Cancel</button>
      <button type="submit" class="btn btn-primary" disabled={addLoading}>
        {#if addLoading}<Loader2 size={13} class="spin" />{/if}Add Scanner
      </button>
    </div>
  </form>
</Modal>

<style>
  :global(.spin){animation:spin .7s linear infinite;}
  @keyframes spin{to{transform:rotate(360deg);}}
</style>
