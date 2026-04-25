<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import { api } from '../lib/api';
  export let data;
  export let onNotify = () => {};
  export let onJobs = () => {};

  const tone = (status) => status === 'running' ? 'warning' : status === 'failed' ? 'danger' : status === 'completed' ? 'success' : 'info';
  $: active = (data.jobs || []).filter((j) => ['queued', 'running', 'waiting'].includes(j.status));

  async function refreshJobs() {
    onJobs(await api.getJobs());
  }

  async function cancel(id) {
    try {
      await api.cancelJob(id);
      await refreshJobs();
      onNotify(`Cancelled ${id}`, 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }
</script>

<section class="grid cols-3">
  <Card variant="kpi-card"><div class="kpi-label">Active</div><strong class="kpi">{active.length}</strong><div class="kpi-note">Running, queued or waiting</div></Card>
  <Card variant="kpi-card"><div class="kpi-label">Running</div><strong class="kpi">{active.filter((j) => j.status === 'running').length}</strong><div class="kpi-note">Currently scanning</div></Card>
  <Card variant="kpi-card"><div class="kpi-label">Queued</div><strong class="kpi">{active.filter((j) => j.status === 'queued').length}</strong><div class="kpi-note">Waiting for resources</div></Card>
</section>

<Card title="Queue control" subtitle="Cancel scans directly from the live queue.">
  <div class="resource-grid">
    {#if active.length === 0}
      <div class="resource-card">
        <div class="resource-head">
          <div class="resource-title"><div class="resource-icon">✓</div><div><h4>No active scans</h4><p>The queue is currently idle.</p></div></div>
          <Badge tone="success" text="idle" />
        </div>
      </div>
    {/if}
    {#each active as job}
      <article class="resource-card">
        <div class="resource-head">
          <div class="resource-title">
            <div class="resource-icon">↻</div>
            <div>
              <h4>{job.device_id || 'Unknown scanner'}</h4>
              <p class="truncate">{job.id}</p>
            </div>
          </div>
          <Badge tone={tone(job.status)} text={job.status} />
        </div>
        <div class="resource-meta">
          <div class="meta-box"><span>Target</span><strong>{job.target_id || '-'}</strong></div>
          <div class="meta-box"><span>Created</span><strong>{job.created_at || '-'}</strong></div>
        </div>
        <div class="stat-track"><div class="stat-fill" style={`width:${job.status === 'running' ? 68 : 28}%`}></div></div>
        <div class="row gap">
          <button class="btn danger" on:click={() => cancel(job.id)}>Cancel job</button>
        </div>
      </article>
    {/each}
  </div>
</Card>
