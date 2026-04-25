<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import { api } from '../lib/api';
  export let data;
  export let onNotify = () => {};

  $: active = (data.jobs || []).filter((job) => ['queued', 'running', 'waiting'].includes(job.status));
  $: completedToday = (data.history || []).filter((job) => job.status === 'completed').length;

  async function cancel(id) {
    try {
      await api.cancelJob(id);
      onNotify(`Cancelled ${id}`, 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }
</script>

<section class="grid cols-3">
  <div class="metric-card info">
    <span class="metric-label">Active jobs</span>
    <strong class="metric-value">{active.length}</strong>
    <span class="metric-foot">Queued, waiting or running</span>
  </div>
  <div class="metric-card success">
    <span class="metric-label">Configured scanners</span>
    <strong class="metric-value">{data.devices.length}</strong>
    <span class="metric-foot">Available in workflow</span>
  </div>
  <div class="metric-card">
    <span class="metric-label">History records</span>
    <strong class="metric-value">{completedToday}</strong>
    <span class="metric-foot">Completed records loaded</span>
  </div>
</section>

<Card title="Scan Queue" subtitle="Real-time operational queue with cancel actions" eyebrow="Operations">
  {#if active.length === 0}
    <div class="empty-state"><div><strong>No active scans right now</strong><span>New jobs will appear here as soon as they start.</span></div></div>
  {:else}
    <div class="table-wrap">
      <table>
        <thead><tr><th>ID</th><th>Status</th><th>Device</th><th>Target</th><th>Actions</th></tr></thead>
        <tbody>
          {#each active as job}
            <tr>
              <td class="code-text">{job.id}</td>
              <td><Badge tone="warning" text={job.status || 'unknown'} /></td>
              <td>{job.device_id || '-'}</td>
              <td>{job.target_id || '-'}</td>
              <td><button class="btn danger" on:click={() => cancel(job.id)}>Cancel</button></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</Card>
