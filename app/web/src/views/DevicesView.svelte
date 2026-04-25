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

  async function refreshDevices() {
    const devices = await api.getDevices();
    onDevices(devices);
  }

  async function discover() {
    try {
      discovered = await api.discoverDevices();
      onNotify(`Found ${discovered.length} scanners`, 'info');
    } catch (error) {
      onNotify(error.message, 'error');
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

<section class="grid cols-2">
  <Card title="Configured scanners" subtitle="Discovery, edit, test, remove">
    <div class="table-wrap">
      <table>
        <thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>
          {#if !data.devices.length}<tr><td colspan="4" class="muted">No scanners configured.</td></tr>{/if}
          {#each data.devices as d}
            <tr>
              <td>{d.name}</td>
              <td>{d.connection_type || 'Unknown'}</td>
              <td><Badge tone={d.status === 'online' ? 'success' : 'warning'} text={d.status || 'unknown'} /></td>
              <td class="row gap">
                <button class="btn ghost" on:click={() => test(d.id)}>Test</button>
                <button class="btn ghost" on:click={() => beginEdit(d)}>Edit</button>
                <button class="btn danger" on:click={() => remove(d.id)}>Remove</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </Card>

  <Card title="Discovery and add" subtitle="Auto discovery + manual registration">
    <div class="row gap">
      <button class="btn primary" on:click={discover}>Discover scanners</button>
    </div>
    <ul class="clean-list top-gap">
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

    <h4>Manual scanner</h4>
    <label>Name <input bind:value={manual.name} placeholder="Office Scanner" /></label>
    <label>URI <input bind:value={manual.uri} placeholder="airscan:escl:..." /></label>
    <button class="btn primary top-gap" on:click={saveManual}>Add manually</button>
  </Card>
</section>

{#if editDevice}
  <div class="dialog-backdrop">
    <div class="dialog">
      <h3>Edit scanner</h3>
      <p class="muted">Backend has no update route, so saving recreates this scanner.</p>
      <label>Name <input bind:value={editDevice.name} /></label>
      <label>URI <input bind:value={editDevice.uri} /></label>
      <div class="row gap top-gap">
        <button class="btn ghost" on:click={() => (editDevice = null)}>Cancel</button>
        <button class="btn primary" on:click={saveEdit}>Save</button>
      </div>
    </div>
  </div>
{/if}
