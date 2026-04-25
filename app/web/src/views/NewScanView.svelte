<script>
  import Card from '../components/ui/Card.svelte';
  import { api } from '../lib/api';
  export let data;
  export let onDone = () => {};

  const steps = ['scanner', 'source', 'profile', 'target', 'filename', 'start'];
  let step = 0;
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

  async function startScan() {
    await api.startScan(form);
    onDone('Scan started successfully', 'success');
    step = 0;
    form.filename_prefix = '';
  }
</script>

<Card title="New Scan Wizard" subtitle="Scanner → source → profile → target → filename/options → start">
  <ol class="wizard-steps">
    {#each steps as label, i}
      <li class:active={i === step} class:done={i < step}>{i + 1}. {label}</li>
    {/each}
  </ol>

  {#if step === 0}
    <label>Scanner
      <select bind:value={form.device_id}>{#each data.devices as d}<option value={d.id}>{d.name} ({d.status || 'unknown'})</option>{/each}</select>
    </label>
  {:else if step === 1}
    <label>Source
      <select bind:value={form.source}><option>Flatbed</option><option>ADF</option></select>
    </label>
  {:else if step === 2}
    <label>Profile
      <select bind:value={form.profile_id}>{#each data.profiles as p}<option value={p.id}>{p.name} ({p.dpi} DPI)</option>{/each}</select>
    </label>
  {:else if step === 3}
    <label>Target
      <select bind:value={form.target_id}>{#each data.targets as t}<option value={t.id}>{t.name} ({t.type})</option>{/each}</select>
    </label>
  {:else if step === 4}
    <label>Filename prefix
      <input bind:value={form.filename_prefix} placeholder="optional" />
    </label>
  {:else}
    <div class="review">
      <p><strong>Scanner:</strong> {form.device_id}</p>
      <p><strong>Source:</strong> {form.source}</p>
      <p><strong>Profile:</strong> {form.profile_id}</p>
      <p><strong>Target:</strong> {form.target_id}</p>
      <p><strong>Filename:</strong> {form.filename_prefix || 'auto-generated'}</p>
    </div>
  {/if}

  <div class="row gap top-gap">
    <button class="btn ghost" disabled={step === 0} on:click={() => (step -= 1)}>Back</button>
    {#if step < steps.length - 1}
      <button class="btn primary" on:click={() => (step += 1)}>Continue</button>
    {:else}
      <button class="btn primary" on:click={startScan}>Start Scan</button>
    {/if}
  </div>
</Card>
