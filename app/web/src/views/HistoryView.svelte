<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import { api } from '../lib/api';
  export let data;
  export let onHistory = () => {};
  export let onNotify = () => {};

  let query = '';
  let status = 'all';

  const tone = (value) => {
    if (value === 'completed') return 'success';
    if (value === 'failed') return 'danger';
    if (['running', 'queued', 'waiting'].includes(value)) return 'warning';
    return 'info';
  };

  $: filtered = (data.history || []).filter((item) => {
    const q = query.trim().toLowerCase();
    const matchQuery = !q || String(item.id || '').toLowerCase().includes(q) || String(item.device_id || '').toLowerCase().includes(q) || String(item.target_id || '').toLowerCase().includes(q);
    const matchStatus = status === 'all' || item.status === status;
    return matchQuery && matchStatus;
  });

  async function refresh() {
    onHistory(await api.getHistory());
  }

  async function clear() {
    try {
      await api.clearHistory();
      await refresh();
      onNotify('Completed history cleared', 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function del(id) {
    try {
      await api.deleteHistoryJob(id);
      await refresh();
      onNotify(`Deleted ${id}`, 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function retry(id) {
    try {
      await api.retryUpload(id);
      onNotify(`Retry requested for ${id}`, 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }
</script>

<section class="grid cols-4">
  <Card variant="kpi-card"><div class="kpi-label">Records</div><strong class="kpi">{data.history.length}</strong><div class="kpi-note">Total jobs in history</div></Card>
  <Card variant="kpi-card"><div class="kpi-label">Completed</div><strong class="kpi">{data.history.filter((i) => i.status === 'completed').length}</strong><div class="kpi-note">Successful jobs</div></Card>
  <Card variant="kpi-card"><div class="kpi-label">Failed</div><strong class="kpi">{data.history.filter((i) => i.status === 'failed').length}</strong><div class="kpi-note">Need attention</div></Card>
  <Card variant="kpi-card"><div class="kpi-label">Filtered</div><strong class="kpi">{filtered.length}</strong><div class="kpi-note">Visible records</div></Card>
</section>

<Card title="History explorer" subtitle="Search by job id, device, target or status.">
  <div class="row gap">
    <input class="search" bind:value={query} placeholder="Search by id, device or target" />
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
            <td class="id-cell">{item.id}</td>
            <td><Badge tone={tone(item.status)} text={item.status} /></td>
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
