<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import { api } from '../lib/api';
  export let data;
  export let onNotify = () => {};

  $: active = (data.jobs || []).filter((j) => ['queued', 'running', 'waiting'].includes(j.status));

  async function cancel(id) {
    try {
      await api.cancelJob(id);
      onNotify(`Cancelled ${id}`, 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }
</script>

<Card title="Active Scans" subtitle="Real-time operational queue">
  <div class="table-wrap">
    <table>
      <thead><tr><th>ID</th><th>Status</th><th>Device</th><th>Target</th><th>Actions</th></tr></thead>
      <tbody>
        {#if active.length === 0}<tr><td colspan="5" class="muted">No active scans right now.</td></tr>{/if}
        {#each active as job}
          <tr>
            <td>{job.id}</td>
            <td><Badge tone="warning" text={job.status} /></td>
            <td>{job.device_id || '-'}</td>
            <td>{job.target_id || '-'}</td>
            <td><button class="btn danger" on:click={() => cancel(job.id)}>Cancel</button></td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</Card>
