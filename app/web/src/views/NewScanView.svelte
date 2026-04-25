<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import { api } from '../lib/api';
  export let data;
  export let onDone = () => {};

  const steps = [
    { id: 'scanner', label: 'Scanner', helper: 'Choose device' },
    { id: 'source', label: 'Source', helper: 'Flatbed or ADF' },
    { id: 'profile', label: 'Profile', helper: 'Quality preset' },
    { id: 'target', label: 'Target', helper: 'Destination' },
    { id: 'filename', label: 'Filename', helper: 'Optional naming' },
    { id: 'start', label: 'Review', helper: 'Start job' }
  ];

  let step = 0;
  let form = {
    device_id: '',
    source: 'Flatbed',
    profile_id: '',
    target_id: '',
    filename_prefix: ''
  };

  $: if (!form.device_id && data.devices.length) form.device_id = data.devices.find((device) => device.is_favorite)?.id || data.devices[0].id;
  $: if (!form.profile_id && data.profiles.length) form.profile_id = data.profiles[0].id;
  $: if (!form.target_id && data.targets.length) form.target_id = data.targets.find((target) => target.is_favorite)?.id || data.targets[0].id;
  $: canStart = Boolean(form.device_id && form.profile_id && form.target_id);
  $: selectedDevice = data.devices.find((device) => device.id === form.device_id);
  $: selectedProfile = data.profiles.find((profile) => profile.id === form.profile_id);
  $: selectedTarget = data.targets.find((target) => target.id === form.target_id);

  async function startScan() {
    if (!canStart) {
      onDone('Please select scanner, profile and target first', 'error');
      return;
    }
    try {
      await api.startScan(form);
      onDone('Scan started successfully', 'success');
      step = 0;
      form.filename_prefix = '';
    } catch (error) {
      onDone(error.message, 'error');
    }
  }
</script>

<Card title="New Scan" subtitle="A focused scan flow optimized for desktop and mobile" eyebrow="Workflow">
  <div class="wizard-layout">
    <aside class="wizard-rail" aria-label="Scan steps">
      {#each steps as item, index}
        <button class:active={index === step} class:done={index < step} on:click={() => (step = index)}>
          <span class="step-index">{index + 1}</span>
          <span class="list-main"><strong>{item.label}</strong><small>{item.helper}</small></span>
        </button>
      {/each}
    </aside>

    <div class="form-grid">
      {#if step === 0}
        <div>
          <h3>Choose scanner</h3>
          <p class="muted">Pick the scanner that should process this job.</p>
        </div>
        <label>Scanner
          <select bind:value={form.device_id}>
            {#each data.devices as device}<option value={device.id}>{device.name} ({device.status || 'unknown'})</option>{/each}
          </select>
        </label>
        {#if !data.devices.length}<div class="empty-state"><div><strong>No scanners configured</strong><span>Add a scanner in Devices first.</span></div></div>{/if}
      {:else if step === 1}
        <div>
          <h3>Source mode</h3>
          <p class="muted">Use ADF for document stacks or Flatbed for single pages.</p>
        </div>
        <label>Source
          <select bind:value={form.source}><option>Flatbed</option><option>ADF</option></select>
        </label>
      {:else if step === 2}
        <div>
          <h3>Scan profile</h3>
          <p class="muted">Choose DPI and quality preset from the backend profiles.</p>
        </div>
        <label>Profile
          <select bind:value={form.profile_id}>
            {#each data.profiles as profile}<option value={profile.id}>{profile.name} ({profile.dpi} DPI)</option>{/each}
          </select>
        </label>
        {#if !data.profiles.length}<div class="empty-state"><div><strong>No profiles loaded</strong><span>Backend did not return scan profiles yet.</span></div></div>{/if}
      {:else if step === 3}
        <div>
          <h3>Destination target</h3>
          <p class="muted">Route the resulting file to a configured target.</p>
        </div>
        <label>Target
          <select bind:value={form.target_id}>
            {#each data.targets as target}<option value={target.id}>{target.name} ({target.type})</option>{/each}
          </select>
        </label>
        {#if !data.targets.length}<div class="empty-state"><div><strong>No targets configured</strong><span>Create a target before starting a scan.</span></div></div>{/if}
      {:else if step === 4}
        <div>
          <h3>Filename options</h3>
          <p class="muted">Leave empty to use automatic naming.</p>
        </div>
        <label>Filename prefix
          <input bind:value={form.filename_prefix} placeholder="invoice, contract, archive ..." />
        </label>
      {:else}
        <div>
          <h3>Review and start</h3>
          <p class="muted">Check the scan route before creating the job.</p>
        </div>
        <div class="review-grid">
          <div class="review-item"><span>Scanner</span><strong>{selectedDevice?.name || form.device_id || '-'}</strong></div>
          <div class="review-item"><span>Source</span><strong>{form.source}</strong></div>
          <div class="review-item"><span>Profile</span><strong>{selectedProfile?.name || form.profile_id || '-'}</strong></div>
          <div class="review-item"><span>Target</span><strong>{selectedTarget?.name || form.target_id || '-'}</strong></div>
          <div class="review-item"><span>Filename</span><strong>{form.filename_prefix || 'auto-generated'}</strong></div>
          <div class="review-item"><span>Status</span><Badge tone={canStart ? 'success' : 'danger'} text={canStart ? 'Ready' : 'Incomplete'} /></div>
        </div>
      {/if}

      <div class="row gap top-gap">
        <button class="btn ghost" disabled={step === 0} on:click={() => (step -= 1)}>Back</button>
        {#if step < steps.length - 1}
          <button class="btn primary" on:click={() => (step += 1)}>Continue</button>
        {:else}
          <button class="btn primary" disabled={!canStart} on:click={startScan}>Start Scan</button>
        {/if}
      </div>
    </div>
  </div>
</Card>
