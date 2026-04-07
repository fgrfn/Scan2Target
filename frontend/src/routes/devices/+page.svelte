<script lang="ts">
  import { onMount } from 'svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import { wsStore } from '$lib/stores/ws.svelte';
  import {
    listDevices,
    discoverDevices,
    addDevice,
    removeDevice,
    setDeviceFavorite,
    checkDeviceOnline,
    type Device,
    type DiscoveredDevice
  } from '$lib/api/devices';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import Modal from '$lib/components/ui/Modal.svelte';

  let devices = $state<Device[]>([]);
  let discovered = $state<DiscoveredDevice[]>([]);
  let loading = $state(true);
  let discovering = $state(false);
  let showDiscoverModal = $state(false);
  let showAddModal = $state(false);

  // Add device form
  let addUri = $state('');
  let addName = $state('');
  let addModel = $state('');
  let addManufacturer = $state('');
  let addLoading = $state(false);

  // Per-device checking state
  let checkingIds = $state<Set<number>>(new Set());
  let removingIds = $state<Set<number>>(new Set());
  let favoriteIds = $state<Set<number>>(new Set());

  onMount(async () => {
    await loadDevices();
  });

  // React to scanner updates from WS
  $effect(() => {
    const upd = wsStore.lastScannerUpdate;
    if (!upd) return;
    devices = devices.map((d) =>
      d.uri === upd.uri ? { ...d, is_online: upd.online, name: upd.name || d.name } : d
    );
  });

  async function loadDevices() {
    loading = true;
    try {
      devices = await listDevices();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load devices', 'error');
    } finally {
      loading = false;
    }
  }

  async function handleDiscover() {
    discovering = true;
    try {
      discovered = await discoverDevices();
      showDiscoverModal = true;
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Discovery failed', 'error');
    } finally {
      discovering = false;
    }
  }

  async function handleAddDiscovered(d: DiscoveredDevice) {
    try {
      const created = await addDevice({
        uri: d.uri,
        name: d.name,
        model: d.model ?? undefined,
        manufacturer: d.manufacturer ?? undefined
      });
      devices = [...devices, created];
      // Remove from discovered list
      discovered = discovered.filter((x) => x.uri !== d.uri);
      showToast(`Added ${created.name}`, 'success');
      if (discovered.length === 0) showDiscoverModal = false;
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to add device', 'error');
    }
  }

  async function handleAddManual(e: SubmitEvent) {
    e.preventDefault();
    addLoading = true;
    try {
      const created = await addDevice({
        uri: addUri,
        name: addName,
        model: addModel || undefined,
        manufacturer: addManufacturer || undefined
      });
      devices = [...devices, created];
      showAddModal = false;
      addUri = '';
      addName = '';
      addModel = '';
      addManufacturer = '';
      showToast(`Added ${created.name}`, 'success');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to add device', 'error');
    } finally {
      addLoading = false;
    }
  }

  async function handleRemove(id: number) {
    if (!confirm('Remove this scanner?')) return;
    removingIds = new Set([...removingIds, id]);
    try {
      await removeDevice(id);
      devices = devices.filter((d) => d.id !== id);
      showToast('Device removed', 'info');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to remove', 'error');
    } finally {
      removingIds.delete(id);
      removingIds = new Set(removingIds);
    }
  }

  async function handleFavorite(d: Device) {
    favoriteIds = new Set([...favoriteIds, d.id]);
    try {
      await setDeviceFavorite(d.id, !d.is_favorite);
      devices = devices.map((x) =>
        x.id === d.id ? { ...x, is_favorite: !x.is_favorite } : x
      );
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to update favorite', 'error');
    } finally {
      favoriteIds.delete(d.id);
      favoriteIds = new Set(favoriteIds);
    }
  }

  async function handleCheck(d: Device) {
    checkingIds = new Set([...checkingIds, d.id]);
    try {
      const result = await checkDeviceOnline(d.id);
      devices = devices.map((x) =>
        x.id === d.id ? { ...x, is_online: result.online, last_checked: new Date().toISOString() } : x
      );
      showToast(`${d.name}: ${result.online ? 'Online' : 'Offline'}`, result.online ? 'success' : 'info');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Check failed', 'error');
    } finally {
      checkingIds.delete(d.id);
      checkingIds = new Set(checkingIds);
    }
  }

  const sortedDevices = $derived(
    [...devices].sort((a, b) => Number(b.is_favorite) - Number(a.is_favorite))
  );

  function formatDate(ts: string | null) {
    if (!ts) return 'Never';
    return new Date(ts).toLocaleString();
  }

  // Filter discovered to not-already-added
  const newDiscovered = $derived(
    discovered.filter((d) => !devices.some((dev) => dev.uri === d.uri))
  );
</script>

<div class="page-header">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="page-title">📡 Devices</h1>
      <p class="page-subtitle">Manage your network scanners</p>
    </div>
    <div class="flex gap-2">
      <button class="btn btn-secondary" onclick={handleDiscover} disabled={discovering}>
        {#if discovering}<Spinner size="sm" />{/if}
        Discover
      </button>
      <button class="btn btn-primary" onclick={() => (showAddModal = true)}>
        + Add Manually
      </button>
    </div>
  </div>
</div>

<div class="page-body">
  {#if loading}
    <div class="flex items-center gap-3">
      <Spinner />
      <span class="text-muted">Loading…</span>
    </div>
  {:else if sortedDevices.length === 0}
    <div class="card">
      <div class="empty-state">
        <div class="empty-icon">📡</div>
        <p>No scanners yet. Click <strong>Discover</strong> or <strong>Add Manually</strong>.</p>
      </div>
    </div>
  {:else}
    <div class="devices-grid">
      {#each sortedDevices as device}
        <div class="card device-card">
          <div class="device-header">
            <div class="device-identity">
              <span
                class={device.is_online === true ? 'online-dot' : device.is_online === false ? 'offline-dot' : 'unknown-dot'}
                title={device.is_online === true ? 'Online' : device.is_online === false ? 'Offline' : 'Unknown'}
              ></span>
              <span class="device-name">{device.name}</span>
              {#if device.is_favorite}
                <span title="Favorite" style="color:var(--color-warning)">★</span>
              {/if}
            </div>
            <div class="device-actions">
              <button
                class="btn btn-ghost btn-icon btn-sm"
                title={device.is_favorite ? 'Unfavorite' : 'Favorite'}
                onclick={() => handleFavorite(device)}
                disabled={favoriteIds.has(device.id)}
              >
                {device.is_favorite ? '★' : '☆'}
              </button>
              <button
                class="btn btn-ghost btn-icon btn-sm"
                title="Check online status"
                onclick={() => handleCheck(device)}
                disabled={checkingIds.has(device.id)}
              >
                {#if checkingIds.has(device.id)}
                  <Spinner size="sm" />
                {:else}
                  ↺
                {/if}
              </button>
              <button
                class="btn btn-danger btn-icon btn-sm"
                title="Remove"
                onclick={() => handleRemove(device.id)}
                disabled={removingIds.has(device.id)}
              >
                ✕
              </button>
            </div>
          </div>

          <div class="device-details">
            <div class="detail-row">
              <span class="detail-label">URI</span>
              <span class="detail-value font-mono" style="font-size:0.78rem">{device.uri}</span>
            </div>
            {#if device.manufacturer || device.model}
              <div class="detail-row">
                <span class="detail-label">Model</span>
                <span class="detail-value">{[device.manufacturer, device.model].filter(Boolean).join(' ')}</span>
              </div>
            {/if}
            <div class="detail-row">
              <span class="detail-label">Last checked</span>
              <span class="detail-value">{formatDate(device.last_checked)}</span>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Discover modal -->
<Modal open={showDiscoverModal} title="Discovered Scanners" onClose={() => (showDiscoverModal = false)} wide={true}>
  {#if newDiscovered.length === 0}
    <div class="empty-state">
      <div class="empty-icon">🔍</div>
      <p>No new scanners found on the network, or all are already added.</p>
    </div>
  {:else}
    <p class="text-muted" style="margin-bottom:16px;font-size:0.875rem">
      {newDiscovered.length} scanner{newDiscovered.length !== 1 ? 's' : ''} found. Click Add to configure.
    </p>
    <div class="discovered-list">
      {#each newDiscovered as d}
        <div class="discovered-item">
          <div class="discovered-info">
            <strong>{d.name}</strong>
            <span class="text-muted font-mono" style="font-size:0.78rem">{d.uri}</span>
            {#if d.manufacturer || d.model}
              <span class="text-dim" style="font-size:0.8rem">{[d.manufacturer, d.model].filter(Boolean).join(' ')}</span>
            {/if}
          </div>
          <button class="btn btn-primary btn-sm" onclick={() => handleAddDiscovered(d)}>
            Add
          </button>
        </div>
      {/each}
    </div>
  {/if}
</Modal>

<!-- Add manually modal -->
<Modal open={showAddModal} title="Add Scanner Manually" onClose={() => (showAddModal = false)}>
  <form onsubmit={handleAddManual}>
    <div class="form-group">
      <label class="form-label" for="add-uri">Scanner URI</label>
      <input id="add-uri" class="form-control" type="text" bind:value={addUri}
        placeholder="escl://192.168.1.100:443/eSCL" required />
      <p class="form-hint">SANE URI or eSCL URL of the scanner.</p>
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
        <input id="add-model" class="form-control" type="text" bind:value={addModel} placeholder="LaserJet 4100" />
      </div>
    </div>
    <div class="flex gap-2 justify-between" style="margin-top:8px">
      <button type="button" class="btn btn-secondary" onclick={() => (showAddModal = false)} disabled={addLoading}>
        Cancel
      </button>
      <button type="submit" class="btn btn-primary" disabled={addLoading}>
        {#if addLoading}<Spinner size="sm" />{/if}
        Add Scanner
      </button>
    </div>
  </form>
</Modal>

<style>
  .devices-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
  }

  .device-card {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .device-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
  }

  .device-identity {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .device-name {
    font-weight: 600;
    font-size: 0.95rem;
  }

  .device-actions {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
  }

  .device-details {
    display: flex;
    flex-direction: column;
    gap: 6px;
    background: var(--color-bg);
    border-radius: var(--radius-sm);
    padding: 10px 12px;
    border: 1px solid var(--color-border-subtle);
  }

  .detail-row {
    display: flex;
    gap: 10px;
    align-items: flex-start;
  }

  .detail-label {
    font-size: 0.75rem;
    color: var(--color-text-dim);
    min-width: 80px;
    flex-shrink: 0;
    padding-top: 2px;
  }

  .detail-value {
    font-size: 0.8rem;
    color: var(--color-text-muted);
    word-break: break-all;
  }

  .unknown-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-text-dim);
  }

  .discovered-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .discovered-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px;
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
  }

  .discovered-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
</style>
