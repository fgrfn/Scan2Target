<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import StatGrid from '../components/StatGrid.svelte';
  import Icon from '../components/ui/Icon.svelte';
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { statusTone, statusKey } from '../lib/status';

  export let data;
  export let onDevices = () => {};
  export let onNotify = () => {};

  let discovered = [];
  let manual = { uri: '', name: '' };
  let editDevice = null;
  let discovering = false;

  $: devices = data.devices || [];
  $: kpiCards = [
    { icon: 'devices', label: $t('kpiConfigured'), value: devices.length, sub: $t('kpiConfiguredSub') },
    { icon: 'check', label: $t('kpiOnline'), value: devices.filter((d) => d.status === 'online').length, sub: $t('kpiOnlineSub') },
    { icon: 'refresh', label: $t('kpiDiscovered'), value: discovered.length, sub: $t('kpiDiscoveredSub') }
  ];

  async function refreshDevices() {
    onDevices(await api.getDevices());
  }

  async function discover() {
    discovering = true;
    try {
      discovered = await api.discoverDevices();
      onNotify($t('foundScanners', { n: discovered.length }), 'info');
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
      onNotify($t('scannerAdded'), 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function remove(id) {
    try {
      await api.removeDevice(id);
      await refreshDevices();
      onNotify($t('scannerRemoved'), 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function check(id) {
    try {
      const res = await api.checkDevice(id);
      await refreshDevices();
      onNotify(res.message || `Status: ${res.status}`, 'info');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function toggleFavorite(device) {
    try {
      await api.setFavoriteDevice(device.id, !device.is_favorite);
      await refreshDevices();
      onNotify(device.is_favorite ? $t('favoriteUnset') : $t('favoriteSet'), 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function saveManual() {
    await add(manual);
    manual = { uri: '', name: '' };
  }

  async function saveEdit() {
    try {
      await api.removeDevice(editDevice.id);
      await api.addDevice({
        uri: editDevice.uri,
        name: editDevice.name,
        make: editDevice.make,
        model: editDevice.model,
        connection_type: editDevice.connection_type
      });
      await refreshDevices();
      onNotify($t('scannerUpdated'), 'success');
      editDevice = null;
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }
</script>

<StatGrid cards={kpiCards} />

<section class="grid cols-2">
  <Card title={$t('deviceInventory')} subtitle={$t('deviceInventorySub')}>
    {#if devices.length === 0}
      <div class="empty-state">
        <Icon name="devices" size={28} />
        <strong>{$t('noDevices')}</strong>
        <p class="muted small">{$t('noDevicesHint')}</p>
        <button class="btn primary" disabled={discovering} on:click={discover}>
          {discovering ? $t('discovering') : $t('discoverBtn')}
        </button>
      </div>
    {:else}
      <div class="resource-grid">
        {#each devices as d (d.id)}
          <article class="resource-card">
            <div class="resource-head">
              <div class="resource-title">
                <div class="resource-icon"><Icon name="devices" /></div>
                <div>
                  <h4>{d.name}</h4>
                  <p class="truncate">{d.uri || d.id}</p>
                </div>
              </div>
              <div class="row gap center">
                <button
                  class="icon-btn"
                  class:fav-active={d.is_favorite}
                  title={d.is_favorite ? $t('unsetFavorite') : $t('setFavorite')}
                  on:click={() => toggleFavorite(d)}
                >
                  <Icon name="star" size={16} filled={d.is_favorite} />
                </button>
                <Badge tone={statusTone(d.status)} text={$t(statusKey(d.status || 'unknown'))} />
              </div>
            </div>
            <div class="resource-meta">
              <div class="meta-box"><span>{$t('connectionLabel')}</span><strong>{d.connection_type || '—'}</strong></div>
              <div class="meta-box"><span>{$t('modelLabel')}</span><strong>{d.model || d.make || '—'}</strong></div>
            </div>
            <div class="row gap">
              <button class="btn ghost" on:click={() => check(d.id)}>{$t('test')}</button>
              <button class="btn ghost" on:click={() => (editDevice = { ...d })}>{$t('edit')}</button>
              <button class="btn danger" on:click={() => remove(d.id)}>{$t('delete')}</button>
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </Card>

  <div class="grid">
    <Card title={$t('discoverTitle')} subtitle={$t('discoverSub')}>
      <button class="btn primary" disabled={discovering} on:click={discover}>
        <Icon name="refresh" size={16} />
        {discovering ? $t('discovering') : $t('discoverBtn')}
      </button>
      <ul class="clean-list top-gap">
        {#if discovered.length === 0}
          <li class="list-row">
            <div><strong>{$t('noDiscovery')}</strong><p class="muted small">{$t('noDiscoveryHint')}</p></div>
          </li>
        {/if}
        {#each discovered as d (d.uri)}
          <li class="list-row">
            <div>
              <strong>{d.name}</strong>
              <p class="muted small truncate">{d.uri}</p>
            </div>
            <button class="btn ghost" disabled={d.already_added} on:click={() => add(d)}>
              {d.already_added ? $t('added') : $t('add')}
            </button>
          </li>
        {/each}
      </ul>
    </Card>

    <Card title={$t('manualTitle')} subtitle={$t('manualSub')}>
      <label>{$t('deviceName')} <input bind:value={manual.name} placeholder="Office Scanner" /></label>
      <label>{$t('deviceUri')} <input bind:value={manual.uri} placeholder="airscan:escl:..." /></label>
      <button class="btn primary top-gap" disabled={!manual.name || !manual.uri} on:click={saveManual}>
        <Icon name="plus" size={16} /> {$t('addManually')}
      </button>
    </Card>
  </div>
</section>

{#if editDevice}
  <div class="dialog-backdrop">
    <div class="dialog">
      <h3>{$t('editScanner')}</h3>
      <p class="muted">{$t('editScannerHint')}</p>
      <label>{$t('deviceName')} <input bind:value={editDevice.name} /></label>
      <label>{$t('deviceUri')} <input bind:value={editDevice.uri} /></label>
      <div class="row gap top-gap">
        <button class="btn ghost" on:click={() => (editDevice = null)}>{$t('cancel')}</button>
        <button class="btn primary" on:click={saveEdit}>{$t('save')}</button>
      </div>
    </div>
  </div>
{/if}
