<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import { api } from '../lib/api';
  export let data;
  export let onHistory = () => {};
  export let onNotify = () => {};

  let query = '';
  let status = 'all';

  $: filtered = (data.history || []).filter((item) => {
    const q = query.trim().toLowerCase();
    const matchQuery = !q || item.id.toLowerCase().includes(q) || (item.device_id || '').toLowerCase().includes(q) || (item.target_id || '').toLowerCase().includes(q);
    const matchStatus = status === 'all' || item.status === status;
    return matchQuery && matchStatus;
  });

  async function refresh() {
    onHistory(await api.getHistory());
  }

  async function clear() {
    await api.clearHistory();
    await refresh();
    onNotify('Completed history cleared', 'success');
  }

  async function del(id) {
    await api.deleteHistoryJob(id);
    await refresh();
    onNotify(`Deleted ${id}`, 'success');
  }

  async function retry(id) {
    await api.retryUpload(id);
    onNotify(`Retry requested for ${id}`, 'success');
  }
</script>

<Card title="History" subtitle="Search and filter job history">
  <div class="row gap">
    <input class="search" bind:value={query} placeholder="Search by id/device/target" />
    <select bind:value={status}>
      <option value="all">All statuses</option>
      <option value="completed">Completed</option>
      <option value="failed">Failed</option>
      <option value="running">Running</option>
      <option value="queued">Queued</option>
      <option value="cancelled">Cancelled</option>
    </select>
    <button class="btn ghost" on:click={refresh}>Refresh</button>
    <button class="btn danger" on:click={clear}>Clear completed</button>
  </div>

  <div class="table-wrap top-gap">
    <table>
      <thead><tr><th>ID</th><th>Status</th><th>Device</th><th>Target</th><th>Created</th><th>Actions</th></tr></thead>
      <tbody>
        {#if filtered.length === 0}<tr><td colspan="6" class="muted">No matching records.</td></tr>{/if}
        {#each filtered as item}
          <tr>
            <td>{item.id}</td>
            <td><Badge tone={item.status === 'completed' ? 'success' : item.status === 'failed' ? 'danger' : 'warning'} text={item.status} /></td>
            <td>{item.device_id || '-'}</td>
            <td>{item.target_id || '-'}</td>
            <td>{item.created_at || '-'}</td>
            <td class="row gap">
              {#if item.status === 'failed'}<button class="btn ghost" on:click={() => retry(item.id)}>Retry</button>{/if}
              <button class="btn danger" on:click={() => del(item.id)}>Delete</button>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</Card>
