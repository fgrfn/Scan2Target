<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import { api } from '../lib/api';
  export let data;
  export let onDevices = () => {};
  export let onNotify = () => {};

  let discovered = [];
  let manual = { uri: '', name: '' };
  let editDevice = null;
  let discovering = false;

  $: onlineCount = (data.devices || []).filter((device) => device.status === 'online').length;

  async function refreshDevices() {
    const devices = await api.getDevices();
    onDevices(devices);
  }

  async function discover() {
    discovering = true;
    try {
      discovered = await api.discoverDevices();
      onNotify(`Found ${discovered.length} scanners`, 'info');
    } catch (error) {
      onNotify(error.message, 'error');
    } finally {
      discovering = false;
    }
  }

  async function add(device) {
    try {
      await api.addDevice({
        uri: device.uri,
        name: device.name,
        make: device.make,
        model: device.model,
        connection_type: device.connection_type
      });
      await refreshDevices();
      onNotify('Scanner added', 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function remove(id) {
    try {
      await api.removeDevice(id);
      await refreshDevices();
      onNotify('Scanner removed', 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function test(id) {
    try {
      const res = await api.checkDevice(id);
      onNotify(res.message || `Status: ${res.status}`, 'info');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function saveManual() {
    if (!manual.uri || !manual.name) {
      onNotify('Name and URI are required', 'error');
      return;
    }
    await add(manual);
    manual = { uri: '', name: '' };
  }

  function beginEdit(device) {
    editDevice = { ...device };
  }

  async function saveEdit() {
    try {
      await api.removeDevice(editDevice.id);
      await api.addDevice({ uri: editDevice.uri, name: editDevice.name, make: editDevice.make, model: editDevice.model, connection_type: editDevice.connection_type });
      await refreshDevices();
      onNotify('Scanner updated (recreated)', 'success');
      editDevice = null;
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }
</script>

<section class="grid cols-3">
  <div class="metric-card success">
    <span class="metric-label">Online</span>
    <strong class="metric-value">{onlineCount}</strong>
    <span class="metric-foot">Scanners currently reachable</span>
  </div>
  <div class="metric-card info">
    <span class="metric-label">Configured</span>
    <strong class="metric-value">{data.devices.length}</strong>
    <span class="metric-foot">Saved device entries</span>
  </div>
  <div class="metric-card warning">
    <span class="metric-label">Discovered</span>
    <strong class="metric-value">{discovered.length}</strong>
    <span class="metric-foot">Latest discovery result</span>
  </div>
</section>

<section class="grid cols-2">
  <Card title="Configured scanners" subtitle="Test, edit and remove scanners" eyebrow="Devices">
    {#if !data.devices.length}
      <div class="empty-state"><div><strong>No scanners configured</strong><span>Run discovery or add a scanner manually.</span></div></div>
    {:else}
      <div class="table-wrap">
        <table>
          <thead><tr><th>Name</th><th>Type</th><th>Status</th><th>URI</th><th>Actions</th></tr></thead>
          <tbody>
            {#each data.devices as device}
              <tr>
                <td><strong>{device.name}</strong></td>
                <td>{device.connection_type || 'Unknown'}</td>
                <td><Badge tone={device.status === 'online' ? 'success' : 'warning'} text={device.status || 'unknown'} /></td>
                <td class="code-text">{device.uri || '-'}</td>
                <td class="row gap">
                  <button class="btn ghost" on:click={() => test(device.id)}>Test</button>
                  <button class="btn ghost" on:click={() => beginEdit(device)}>Edit</button>
                  <button class="btn danger" on:click={() => remove(device.id)}>Remove</button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </Card>

  <Card title="Discovery & manual add" subtitle="Search local scanners or register by URI" eyebrow="Setup">
    <div class="row gap">
      <button class="btn primary" disabled={discovering} on:click={discover}>{discovering ? 'Discovering...' : 'Discover scanners'}</button>
    </div>

    <div class="list-stack top-gap">
      {#if discovered.length === 0}
        <div class="empty-state"><div><strong>No discovery results yet</strong><span>Start discovery to list network scanners.</span></div></div>
      {/if}
      {#each discovered as device}
        <div class="list-row">
          <div class="list-main">
            <strong>{device.name}</strong>
            <span>{device.uri}</span>
          </div>
          <button class="btn ghost" disabled={device.already_added} on:click={() => add(device)}>{device.already_added ? 'Added' : 'Add'}</button>
        </div>
      {/each}
    </div>

    <div class="form-grid top-gap">
      <label>Name <input bind:value={manual.name} placeholder="Office Scanner" /></label>
      <label>URI <input bind:value={manual.uri} placeholder="airscan:escl:..." /></label>
      <button class="btn secondary" on:click={saveManual}>Add manually</button>
    </div>
  </Card>
</section>

{#if editDevice}
  <div class="dialog-backdrop">
    <div class="dialog">
      <h3>Edit scanner</h3>
      <p class="muted">Backend has no update route, so saving recreates this scanner.</p>
      <div class="form-grid">
        <label>Name <input bind:value={editDevice.name} /></label>
        <label>URI <input bind:value={editDevice.uri} /></label>
      </div>
      <div class="row gap top-gap">
        <button class="btn ghost" on:click={() => (editDevice = null)}>Cancel</button>
        <button class="btn primary" on:click={saveEdit}>Save</button>
      </div>
    </div>
  </div>
{/if}
