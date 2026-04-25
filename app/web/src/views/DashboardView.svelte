<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  export let data;
  export let onNavigate = () => {};

  $: overview = data.stats.overview || {};
  $: active = (data.jobs || []).filter((j) => ['queued', 'running'].includes(j.status));
  $: recent = (data.history || []).slice(0, 5);
</script>

<section class="grid cols-4">
  <Card title="Total scans"><strong class="kpi">{overview.total_scans || 0}</strong></Card>
  <Card title="Today"><strong class="kpi">{overview.today_scans || 0}</strong></Card>
  <Card title="Success rate"><strong class="kpi">{overview.success_rate || 0}%</strong></Card>
  <Card title="Avg/day"><strong class="kpi">{overview.average_scans_per_day || 0}</strong></Card>
</section>

<section class="grid cols-2">
  <Card title="Quick actions" subtitle="Central scan workflow">
    <div class="row gap">
      <button class="btn primary" on:click={() => onNavigate('new-scan')}>Start New Scan</button>
      <button class="btn ghost" on:click={() => onNavigate('devices')}>Manage Devices</button>
      <button class="btn ghost" on:click={() => onNavigate('targets')}>Manage Targets</button>
    </div>
  </Card>

  <Card title="Active scans" subtitle={`${active.length} jobs in progress`}>
    {#if active.length === 0}<p class="muted">No active scans.</p>{/if}
    {#each active as job}
      <div class="list-row"><span>{job.id}</span><Badge tone="info" text={job.status} /></div>
    {/each}
  </Card>
</section>

<Card title="Recent activity">
  <div class="table-wrap">
    <table>
      <thead><tr><th>ID</th><th>Status</th><th>Device</th><th>Created</th></tr></thead>
      <tbody>
        {#if recent.length === 0}<tr><td colspan="4" class="muted">No history yet.</td></tr>{/if}
        {#each recent as item}
          <tr>
            <td>{item.id}</td>
            <td><Badge tone={item.status === 'completed' ? 'success' : item.status === 'failed' ? 'danger' : 'warning'} text={item.status} /></td>
            <td>{item.device_id || '-'}</td>
            <td>{item.created_at || '-'}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</Card>
