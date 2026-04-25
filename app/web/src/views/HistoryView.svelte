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
    const id = String(item.id || '').toLowerCase();
    const device = String(item.device_id || '').toLowerCase();
    const target = String(item.target_id || '').toLowerCase();
    const matchQuery = !q || id.includes(q) || device.includes(q) || target.includes(q);
    const matchStatus = status === 'all' || item.status === status;
    return matchQuery && matchStatus;
  });
  $: failedCount = (data.history || []).filter((item) => item.status === 'failed').length;
  $: completedCount = (data.history || []).filter((item) => item.status === 'completed').length;

  async function refresh() {
    try {
      onHistory(await api.getHistory());
    } catch (error) {
      onNotify(error.message, 'error');
    }
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

<section class="grid cols-3">
  <div class="metric-card success">
    <span class="metric-label">Completed</span>
    <strong class="metric-value">{completedCount}</strong>
    <span class="metric-foot">Loaded history records</span>
  </div>
  <div class="metric-card warning">
    <span class="metric-label">Filtered</span>
    <strong class="metric-value">{filtered.length}</strong>
    <span class="metric-foot">Matching current filter</span>
  </div>
  <div class="metric-card">
    <span class="metric-label">Failed</span>
    <strong class="metric-value">{failedCount}</strong>
    <span class="metric-foot">Retry candidates</span>
  </div>
</section>

<Card title="History" subtitle="Search, filter, retry and remove scan jobs" eyebrow="Archive">
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
            <td class="code-text">{item.id}</td>
            <td><Badge tone={item.status === 'completed' ? 'success' : item.status === 'failed' ? 'danger' : 'warning'} text={item.status || 'unknown'} /></td>
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
