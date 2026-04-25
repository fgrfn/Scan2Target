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

  const tone = (status) => status === 'online' ? 'success' : status === 'offline' ? 'danger' : 'warning';

  async function refreshDevices() {
    onDevices(await api.getDevices());
  }

  async function discover() {
    try {
      discovering = true;
      discovered = await api.discoverDevices();
      onNotify(`Found ${discovered.length} scanner${discovered.length === 1 ? '' : 's'}`, 'info');
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
      await refreshDevices();
      onNotify(res.message || `Status: ${res.status}`, 'info');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function saveManual() {
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
      onNotify('Scanner updated', 'success');
      editDevice = null;
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }
</script>

<section class="grid cols-3">
  <Card variant="kpi-card"><div class="kpi-label">Configured</div><strong class="kpi">{data.devices.length}</strong><div class="kpi-note">Known scanners</div></Card>
  <Card variant="kpi-card"><div class="kpi-label">Online</div><strong class="kpi">{data.devices.filter((d) => d.status === 'online').length}</strong><div class="kpi-note">Reachable right now</div></Card>
  <Card variant="kpi-card"><div class="kpi-label">Discovered</div><strong class="kpi">{discovered.length}</strong><div class="kpi-note">Latest discovery result</div></Card>
</section>

<section class="grid cols-2">
  <Card title="Scanner inventory" subtitle="Card-based device overview with quick actions.">
    <div class="resource-grid">
      {#if !data.devices.length}
        <div class="resource-card"><div class="resource-head"><div class="resource-title"><div class="resource-icon">▣</div><div><h4>No scanners configured</h4><p>Use discovery or add a manual URI.</p></div></div><Badge tone="warning" text="empty" /></div></div>
      {/if}
      {#each data.devices as d}
        <article class="resource-card">
          <div class="resource-head">
            <div class="resource-title">
              <div class="resource-icon">▣</div>
              <div>
                <h4>{d.name}</h4>
                <p class="truncate">{d.uri || d.id}</p>
              </div>
            </div>
            <Badge tone={tone(d.status)} text={d.status || 'unknown'} />
          </div>
          <div class="resource-meta">
            <div class="meta-box"><span>Connection</span><strong>{d.connection_type || 'Unknown'}</strong></div>
            <div class="meta-box"><span>Model</span><strong>{d.model || d.make || '-'}</strong></div>
          </div>
          <div class="row gap">
            <button class="btn ghost" on:click={() => test(d.id)}>Test</button>
            <button class="btn ghost" on:click={() => beginEdit(d)}>Edit</button>
            <button class="btn danger" on:click={() => remove(d.id)}>Remove</button>
          </div>
        </article>
      {/each}
    </div>
  </Card>

  <div class="grid">
    <Card title="Discovery" subtitle="Find compatible scanners on the network.">
      <button class="btn primary" disabled={discovering} on:click={discover}>{discovering ? 'Discovering…' : 'Discover scanners'}</button>
      <ul class="clean-list top-gap">
        {#if discovered.length === 0}<li class="list-row"><div><strong>No discovery result yet</strong><p class="muted small">Run discovery to populate this list.</p></div></li>{/if}
        {#each discovered as d}
          <li class="list-row">
            <div>
              <strong>{d.name}</strong>
              <p class="muted small">{d.uri}</p>
            </div>
            <button class="btn ghost" disabled={d.already_added} on:click={() => add(d)}>{d.already_added ? 'Added' : 'Add'}</button>
          </li>
        {/each}
      </ul>
    </Card>

    <Card title="Manual scanner" subtitle="Register an airscan/eSCL or SANE URI manually.">
      <label>Name <input bind:value={manual.name} placeholder="Office Scanner" /></label>
      <label>URI <input bind:value={manual.uri} placeholder="airscan:escl:..." /></label>
      <button class="btn primary top-gap" disabled={!manual.name || !manual.uri} on:click={saveManual}>Add manually</button>
    </Card>
  </div>
</section>

{#if editDevice}
  <div class="dialog-backdrop">
    <div class="dialog">
      <h3>Edit scanner</h3>
      <p class="muted">The backend currently recreates the scanner when saving edited values.</p>
      <label>Name <input bind:value={editDevice.name} /></label>
      <label>URI <input bind:value={editDevice.uri} /></label>
      <div class="row gap top-gap">
        <button class="btn ghost" on:click={() => (editDevice = null)}>Cancel</button>
        <button class="btn primary" on:click={saveEdit}>Save</button>
      </div>
    </div>
  </div>
{/if}
