<script lang="ts">
  import { onMount } from 'svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import { wsStore } from '$lib/stores/ws.svelte';
  import {
    listDevices, discoverDevices, addDevice, removeDevice,
    setDeviceFavorite, checkDeviceOnline,
    type Device, type DiscoveredDevice
  } from '$lib/api/devices';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import Modal from '$lib/components/ui/Modal.svelte';
  import { Printer, Plus, Search, RefreshCw, Trash2, Star, StarOff,
           Wifi, WifiOff, Clock, Loader2 } from 'lucide-svelte';

  let devices           = $state<Device[]>([]);
  let discovered        = $state<DiscoveredDevice[]>([]);
  let loading           = $state(true);
  let discovering       = $state(false);
  let showDiscoverModal = $state(false);
  let showAddModal      = $state(false);

  let addUri          = $state('');
  let addName         = $state('');
  let addModel        = $state('');
  let addManufacturer = $state('');
  let addLoading      = $state(false);

  let checkingIds  = $state<Set<number>>(new Set());
  let removingIds  = $state<Set<number>>(new Set());
  let favoriteIds  = $state<Set<number>>(new Set());

  const sortedDevices = $derived([...devices].sort((a,b) => Number(b.is_favorite)-Number(a.is_favorite)));
  const newDiscovered = $derived(discovered.filter(d => !devices.some(dev => dev.uri === d.uri)));

  onMount(() => loadDevices());

  $effect(() => {
    const upd = wsStore.lastScannerUpdate;
    if (!upd) return;
    devices = devices.map(d => d.uri === upd.uri ? { ...d, is_online: upd.online, name: upd.name || d.name } : d);
  });

  async function loadDevices() {
    loading = true;
    try { devices = await listDevices(); }
    catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Failed', 'error'); }
    finally { loading = false; }
  }

  async function handleDiscover() {
    discovering = true;
    try { discovered = await discoverDevices(); showDiscoverModal = true; }
    catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Discovery failed', 'error'); }
    finally { discovering = false; }
  }

  async function handleAddDiscovered(d: DiscoveredDevice) {
    try {
      const created = await addDevice({ uri: d.uri, name: d.name, model: d.model ?? undefined, manufacturer: d.manufacturer ?? undefined });
      devices = [...devices, created];
      discovered = discovered.filter(x => x.uri !== d.uri);
      showToast(`Added ${created.name}`, 'success');
      if (discovered.length === 0) showDiscoverModal = false;
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Failed', 'error'); }
  }

  async function handleAddManual(e: SubmitEvent) {
    e.preventDefault(); addLoading = true;
    try {
      const created = await addDevice({ uri: addUri, name: addName, model: addModel || undefined, manufacturer: addManufacturer || undefined });
      devices = [...devices, created];
      showAddModal = false;
      addUri = ''; addName = ''; addModel = ''; addManufacturer = '';
      showToast(`Added ${created.name}`, 'success');
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Failed', 'error'); }
    finally { addLoading = false; }
  }

  async function handleRemove(id: number) {
    if (!confirm('Remove this scanner?')) return;
    removingIds = new Set([...removingIds, id]);
    try {
      await removeDevice(id);
      devices = devices.filter(d => d.id !== id);
      showToast('Scanner removed', 'info');
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Failed', 'error'); }
    finally { removingIds.delete(id); removingIds = new Set(removingIds); }
  }

  async function handleFavorite(d: Device) {
    favoriteIds = new Set([...favoriteIds, d.id]);
    try {
      await setDeviceFavorite(d.id, !d.is_favorite);
      devices = devices.map(x => x.id === d.id ? { ...x, is_favorite: !x.is_favorite } : x);
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Failed', 'error'); }
    finally { favoriteIds.delete(d.id); favoriteIds = new Set(favoriteIds); }
  }

  async function handleCheck(d: Device) {
    checkingIds = new Set([...checkingIds, d.id]);
    try {
      const result = await checkDeviceOnline(d.id);
      devices = devices.map(x => x.id === d.id ? { ...x, is_online: result.online, last_checked: new Date().toISOString() } : x);
      showToast(`${d.name}: ${result.online ? 'Online' : 'Offline'}`, result.online ? 'success' : 'info');
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : 'Check failed', 'error'); }
    finally { checkingIds.delete(d.id); checkingIds = new Set(checkingIds); }
  }

  function fmtDate(ts: string | null) {
    if (!ts) return 'Never';
    const d = new Date(ts);
    const now = new Date();
    const diff = Math.floor((now.getTime() - d.getTime()) / 1000);
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
    return d.toLocaleDateString();
  }
</script>

<div class="page-wrap">
  <!-- Header -->
  <div class="page-header">
    <div>
      <h1 class="page-title">Devices</h1>
      <p class="page-sub">Manage your network scanners</p>
    </div>
    <div class="flex gap-2 flex-wrap">
      <button class="btn btn-secondary" onclick={handleDiscover} disabled={discovering}>
        {#if discovering}<Loader2 size={15} class="animate-spin" />{:else}<Search size={15} />{/if}
        Discover
      </button>
      <button class="btn btn-primary" onclick={() => (showAddModal = true)}>
        <Plus size={15} /> Add Scanner
      </button>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center gap-3 text-zinc-500 py-12"><Spinner /><span>Loading…</span></div>
  {:else if sortedDevices.length === 0}
    <div class="card">
      <div class="empty-state">
        <Printer size={40} class="text-zinc-800" />
        <p>No scanners yet.<br />Click <strong class="text-zinc-400">Discover</strong> or <strong class="text-zinc-400">Add Scanner</strong>.</p>
      </div>
    </div>
  {:else}
    <div class="grid gap-4" style="grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));">
      {#each sortedDevices as device}
        <div class="card flex flex-col gap-0 overflow-hidden">
          <!-- Card header -->
          <div class="flex items-start justify-between p-4 pb-3">
            <div class="flex items-center gap-2.5 min-w-0">
              <!-- Status dot -->
              <span class="{device.is_online === true ? 'dot-online' : device.is_online === false ? 'dot-offline' : 'dot-unknown'}"
                    title="{device.is_online === true ? 'Online' : device.is_online === false ? 'Offline' : 'Unknown'}">
              </span>
              <div class="min-w-0">
                <p class="font-semibold text-zinc-100 text-sm truncate">{device.name}</p>
                {#if device.manufacturer || device.model}
                  <p class="text-xs text-zinc-500 truncate">
                    {[device.manufacturer, device.model].filter(Boolean).join(' ')}
                  </p>
                {/if}
              </div>
              {#if device.is_favorite}
                <Star size={13} class="text-amber-400 flex-shrink-0 ml-1" fill="currentColor" />
              {/if}
            </div>

            <!-- Actions -->
            <div class="flex gap-1 flex-shrink-0 ml-2">
              <button class="btn btn-ghost btn-icon btn-sm" title={device.is_favorite ? 'Unfavorite' : 'Favorite'}
                      onclick={() => handleFavorite(device)} disabled={favoriteIds.has(device.id)}>
                {#if device.is_favorite}
                  <Star size={14} fill="currentColor" class="text-amber-400" />
                {:else}
                  <StarOff size={14} />
                {/if}
              </button>
              <button class="btn btn-ghost btn-icon btn-sm" title="Check status"
                      onclick={() => handleCheck(device)} disabled={checkingIds.has(device.id)}>
                {#if checkingIds.has(device.id)}
                  <Loader2 size={14} class="animate-spin" />
                {:else}
                  <RefreshCw size={14} />
                {/if}
              </button>
              <button class="btn btn-ghost btn-icon btn-sm hover:text-red-400" title="Remove"
                      onclick={() => handleRemove(device.id)} disabled={removingIds.has(device.id)}>
                <Trash2 size={14} />
              </button>
            </div>
          </div>

          <!-- Details -->
          <div class="mx-4 mb-4 bg-zinc-950/60 rounded-lg p-3 border border-zinc-800/60 flex flex-col gap-1.5">
            <div class="flex gap-2 items-start">
              <span class="text-zinc-600 text-xs flex-shrink-0 w-16 pt-0.5">URI</span>
              <span class="text-zinc-400 text-xs font-mono truncate">{device.uri}</span>
            </div>
            <div class="flex gap-2 items-center">
              <Clock size={10} class="text-zinc-700 flex-shrink-0 ml-0.5" />
              <span class="text-zinc-600 text-xs">{fmtDate(device.last_checked)}</span>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Discover modal -->
<Modal open={showDiscoverModal} title="Discovered Scanners" onClose={() => (showDiscoverModal = false)} wide>
  {#if newDiscovered.length === 0}
    <div class="empty-state py-8">
      <Search size={32} class="text-zinc-800" />
      <p>No new scanners found on the network.</p>
    </div>
  {:else}
    <p class="text-sm text-zinc-500 mb-4">{newDiscovered.length} scanner{newDiscovered.length !== 1 ? 's' : ''} found</p>
    <div class="flex flex-col gap-2">
      {#each newDiscovered as d}
        <div class="flex items-center justify-between gap-3 p-3 bg-zinc-800/40 border border-zinc-700/40 rounded-lg">
          <div class="flex items-center gap-3 min-w-0">
            <Printer size={18} class="text-zinc-500 flex-shrink-0" />
            <div class="min-w-0">
              <p class="font-medium text-zinc-200 text-sm">{d.name}</p>
              <p class="text-xs text-zinc-600 font-mono truncate">{d.uri}</p>
              {#if d.manufacturer || d.model}
                <p class="text-xs text-zinc-500">{[d.manufacturer, d.model].filter(Boolean).join(' ')}</p>
              {/if}
            </div>
          </div>
          <button class="btn btn-primary btn-sm flex-shrink-0" onclick={() => handleAddDiscovered(d)}>Add</button>
        </div>
      {/each}
    </div>
  {/if}
</Modal>

<!-- Add manually modal -->
<Modal open={showAddModal} title="Add Scanner Manually" onClose={() => (showAddModal = false)}>
  <form onsubmit={handleAddManual} class="flex flex-col gap-4">
    <div class="form-group">
      <label class="form-label" for="add-uri">Scanner URI</label>
      <input id="add-uri" class="form-control" type="text" bind:value={addUri}
             placeholder="escl://192.168.1.100:443/eSCL" required />
      <span class="form-hint">SANE URI or eSCL URL of the scanner.</span>
    </div>
    <div class="form-group">
      <label class="form-label" for="add-name">Display Name</label>
      <input id="add-name" class="form-control" type="text" bind:value={addName}
             placeholder="Office Scanner" required />
    </div>
    <div class="form-row">
      <div class="form-group">
        <label class="form-label" for="add-mfr">Manufacturer</label>
        <input id="add-mfr" class="form-control" type="text" bind:value={addManufacturer} placeholder="HP" />
      </div>
      <div class="form-group">
        <label class="form-label" for="add-model">Model</label>
        <input id="add-model" class="form-control" type="text" bind:value={addModel} placeholder="LaserJet 4150" />
      </div>
    </div>
    <div class="flex gap-2 justify-end pt-1">
      <button type="button" class="btn btn-secondary" onclick={() => (showAddModal = false)}>Cancel</button>
      <button type="submit" class="btn btn-primary" disabled={addLoading}>
        {#if addLoading}<Loader2 size={14} class="animate-spin" />{/if}
        Add Scanner
      </button>
    </div>
  </form>
</Modal>

<style>
  :global(.animate-spin) { animation: spin 0.75s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
