<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import { api } from '../lib/api';
  export let data;
  export let onDone = () => {};

  const steps = [
    { id: 'scanner', label: 'Scanner', hint: 'Choose device' },
    { id: 'source', label: 'Source', hint: 'Flatbed or ADF' },
    { id: 'profile', label: 'Profile', hint: 'DPI and format' },
    { id: 'target', label: 'Target', hint: 'Delivery route' },
    { id: 'name', label: 'Filename', hint: 'Optional prefix' },
    { id: 'review', label: 'Launch', hint: 'Review and start' }
  ];

  let step = 0;
  let starting = false;
  let form = {
    device_id: '',
    source: 'Flatbed',
    profile_id: '',
    target_id: '',
    filename_prefix: ''
  };

  $: if (!form.device_id && data.devices.length) form.device_id = data.devices.find((d) => d.is_favorite)?.id || data.devices[0].id;
  $: if (!form.profile_id && data.profiles.length) form.profile_id = data.profiles[0].id;
  $: if (!form.target_id && data.targets.length) form.target_id = data.targets.find((t) => t.is_favorite)?.id || data.targets[0].id;
  $: selectedDevice = data.devices.find((d) => d.id === form.device_id);
  $: selectedProfile = data.profiles.find((p) => p.id === form.profile_id);
  $: selectedTarget = data.targets.find((t) => t.id === form.target_id);

  async function startScan() {
    try {
      starting = true;
      await api.startScan(form);
      onDone('Scan started successfully', 'success');
      step = 0;
      form.filename_prefix = '';
    } catch (error) {
      onDone(error.message, 'error');
    } finally {
      starting = false;
    }
  }
</script>

<div class="scan-layout">
  <Card title="Scan flow" subtitle="One clean path from scanner to delivery.">
    <div class="step-rail">
      {#each steps as item, i}
        <div class="step-item" class:active={i === step} class:done={i < step}>
          <div class="step-index">{i < step ? '✓' : i + 1}</div>
          <div class="step-label"><strong>{item.label}</strong><span>{item.hint}</span></div>
        </div>
      {/each}
    </div>
  </Card>

  <Card title={steps[step].label} subtitle={steps[step].hint}>
    {#if step === 0}
      {#if data.devices.length === 0}
        <div class="list-row"><div><strong>No scanners configured</strong><p class="muted small">Add or discover a scanner before launching a scan.</p></div><Badge tone="warning" text="setup" /></div>
      {:else}
        <div class="choice-grid">
          {#each data.devices as d}
            <button class="choice-card" class:selected={form.device_id === d.id} on:click={() => (form.device_id = d.id)}>
              <div class="choice-icon">▣</div>
              <h4>{d.name}</h4>
              <p>{d.connection_type || 'Unknown connection'} · {d.status || 'unknown'}</p>
            </button>
          {/each}
        </div>
      {/if}
    {:else if step === 1}
      <div class="choice-grid">
        {#each ['Flatbed', 'ADF'] as source}
          <button class="choice-card" class:selected={form.source === source} on:click={() => (form.source = source)}>
            <div class="choice-icon">{source === 'ADF' ? '⇉' : '▤'}</div>
            <h4>{source}</h4>
            <p>{source === 'ADF' ? 'Automatic document feeder for multi-page documents.' : 'Single page scan from the flatbed glass.'}</p>
          </button>
        {/each}
      </div>
    {:else if step === 2}
      {#if data.profiles.length === 0}
        <p class="muted">No scan profiles available.</p>
      {:else}
        <div class="choice-grid">
          {#each data.profiles as p}
            <button class="choice-card" class:selected={form.profile_id === p.id} on:click={() => (form.profile_id = p.id)}>
              <div class="choice-icon">◎</div>
              <h4>{p.name}</h4>
              <p>{p.dpi || '-'} DPI · {p.format || p.mode || 'default profile'}</p>
            </button>
          {/each}
        </div>
      {/if}
    {:else if step === 3}
      {#if data.targets.length === 0}
        <p class="muted">No targets configured.</p>
      {:else}
        <div class="choice-grid">
          {#each data.targets as t}
            <button class="choice-card" class:selected={form.target_id === t.id} on:click={() => (form.target_id = t.id)}>
              <div class="choice-icon">→</div>
              <h4>{t.name}</h4>
              <p>{t.type} · {t.enabled === false ? 'disabled' : 'enabled'}</p>
            </button>
          {/each}
        </div>
      {/if}
    {:else if step === 4}
      <label>Filename prefix
        <input bind:value={form.filename_prefix} placeholder="optional, e.g. invoice, contract, archive" />
      </label>
      <p class="muted small">Leave empty for automatic naming. The backend will still generate a unique filename.</p>
    {:else}
      <div class="review-grid">
        <div class="review-item"><span>Scanner</span><strong>{selectedDevice?.name || form.device_id || '-'}</strong></div>
        <div class="review-item"><span>Source</span><strong>{form.source}</strong></div>
        <div class="review-item"><span>Profile</span><strong>{selectedProfile?.name || form.profile_id || '-'}</strong></div>
        <div class="review-item"><span>Target</span><strong>{selectedTarget?.name || form.target_id || '-'}</strong></div>
        <div class="review-item"><span>Filename</span><strong>{form.filename_prefix || 'auto-generated'}</strong></div>
        <div class="review-item"><span>Status</span><strong>Ready to start</strong></div>
      </div>
    {/if}

    <div class="row gap top-gap">
      <button class="btn ghost" disabled={step === 0 || starting} on:click={() => (step -= 1)}>Back</button>
      {#if step < steps.length - 1}
        <button class="btn primary" disabled={starting} on:click={() => (step += 1)}>Continue</button>
      {:else}
        <button class="btn primary" disabled={starting || !form.device_id || !form.profile_id || !form.target_id} on:click={startScan}>{starting ? 'Starting…' : 'Start scan'}</button>
      {/if}
    </div>
  </Card>
</div>
