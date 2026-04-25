<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  export let data;
  export let onNavigate = () => {};

  $: overview = data.stats.overview || {};
  $: active = (data.jobs || []).filter((job) => ['queued', 'running', 'waiting'].includes(job.status));
  $: recent = (data.history || []).slice(0, 6);
  $: online = (data.devices || []).filter((device) => device.status === 'online').length;
  $: enabledTargets = (data.targets || []).filter((target) => target.enabled !== false).length;
  $: successRate = Number(overview.success_rate || 0);
</script>

<section class="hero-panel">
  <div class="hero-copy">
    <span class="eyebrow">Unified scan workflow</span>
    <h2>Scan, route, done.</h2>
    <p>Ein neues Command-Center für deine Scanner: schnelle Aktionen, klare Zustände und alle Ziele an einem Ort. Die API-Verträge bleiben unverändert.</p>
    <div class="hero-actions">
      <button class="btn primary" on:click={() => onNavigate('new-scan')}>◎ Start New Scan</button>
      <button class="btn ghost" on:click={() => onNavigate('devices')}>▣ Manage Devices</button>
      <button class="btn ghost" on:click={() => onNavigate('targets')}>↗ Manage Targets</button>
    </div>
  </div>

  <div class="hero-stat-card">
    <div>
      <span>Success rate</span>
      <strong>{successRate}%</strong>
    </div>
    <p class="muted">{overview.total_scans || 0} total scans · {overview.today_scans || 0} today</p>
  </div>
</section>

<section class="grid cols-4">
  <div class="metric-card success">
    <span class="metric-label">Online scanners</span>
    <strong class="metric-value">{online}</strong>
    <span class="metric-foot">{data.devices.length} configured</span>
  </div>
  <div class="metric-card info">
    <span class="metric-label">Active jobs</span>
    <strong class="metric-value">{active.length}</strong>
    <span class="metric-foot">Queued, running or waiting</span>
  </div>
  <div class="metric-card warning">
    <span class="metric-label">Targets</span>
    <strong class="metric-value">{enabledTargets}</strong>
    <span class="metric-foot">Enabled destinations</span>
  </div>
  <div class="metric-card">
    <span class="metric-label">Average/day</span>
    <strong class="metric-value">{overview.average_scans_per_day || 0}</strong>
    <span class="metric-foot">30 day trend</span>
  </div>
</section>

<section class="dashboard-grid">
  <Card title="Current queue" subtitle="Jobs that need attention or are still processing" eyebrow="Live">
    {#if active.length === 0}
      <div class="empty-state"><div><strong>No active scans</strong><span>Your queue is clean.</span></div></div>
    {:else}
      <div class="list-stack">
        {#each active as job}
          <div class="list-row">
            <div class="list-main">
              <strong>{job.id}</strong>
              <span>{job.device_id || 'Unknown scanner'} → {job.target_id || 'No target'}</span>
            </div>
            <Badge tone="warning" text={job.status} />
          </div>
        {/each}
      </div>
    {/if}
  </Card>

  <Card title="Quick routing" subtitle="Common admin actions" eyebrow="Actions" variant="filled">
    <div class="list-stack">
      <button class="btn primary" on:click={() => onNavigate('new-scan')}>Create scan job</button>
      <button class="btn ghost" on:click={() => onNavigate('history')}>Open history</button>
      <button class="btn ghost" on:click={() => onNavigate('statistics')}>View analytics</button>
    </div>
  </Card>
</section>

<Card title="Recent activity" subtitle="Latest completed, failed or queued scan jobs" eyebrow="History">
  <div class="table-wrap">
    <table>
      <thead><tr><th>ID</th><th>Status</th><th>Device</th><th>Target</th><th>Created</th></tr></thead>
      <tbody>
        {#if recent.length === 0}<tr><td colspan="5" class="muted">No history yet.</td></tr>{/if}
        {#each recent as item}
          <tr>
            <td class="code-text">{item.id}</td>
            <td><Badge tone={item.status === 'completed' ? 'success' : item.status === 'failed' ? 'danger' : 'warning'} text={item.status || 'unknown'} /></td>
            <td>{item.device_id || '-'}</td>
            <td>{item.target_id || '-'}</td>
            <td>{item.created_at || '-'}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</Card>
