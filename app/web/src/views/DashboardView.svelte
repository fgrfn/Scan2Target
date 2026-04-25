<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  export let data;
  export let onNavigate = () => {};

  const statusTone = (status) => {
    if (status === 'completed' || status === 'online') return 'success';
    if (status === 'failed' || status === 'offline') return 'danger';
    if (['queued', 'running', 'waiting'].includes(status)) return 'warning';
    return 'info';
  };

  $: overview = data.stats.overview || {};
  $: active = (data.jobs || []).filter((j) => ['queued', 'running', 'waiting'].includes(j.status));
  $: recent = (data.history || []).slice(0, 6);
  $: onlineDevices = (data.devices || []).filter((d) => d.status === 'online').length;
  $: enabledTargets = (data.targets || []).filter((t) => t.enabled !== false).length;
  $: success = Number(overview.success_rate || 0);
</script>

<Card variant="hero-card">
  <div class="hero-content">
    <div>
      <div class="eyebrow">Modern Scan Hub</div>
      <h2 class="hero-title">Scan. Route. Deliver.</h2>
      <p class="hero-copy">A cleaner command-center UI for your network scanners with fast actions, live queue state and delivery status at a glance.</p>
    </div>

    <div class="hero-actions">
      <button class="btn primary" on:click={() => onNavigate('new-scan')}>◉ Start scan</button>
      <button class="btn ghost" on:click={() => onNavigate('devices')}>▣ Manage devices</button>
      <button class="btn ghost" on:click={() => onNavigate('targets')}>→ Targets</button>
    </div>

    <div class="hero-metrics">
      <div class="hero-metric"><span>Online scanners</span><strong>{onlineDevices}/{data.devices.length || 0}</strong></div>
      <div class="hero-metric"><span>Active queue</span><strong>{active.length}</strong></div>
      <div class="hero-metric"><span>Enabled targets</span><strong>{enabledTargets}</strong></div>
    </div>
  </div>
</Card>

<section class="grid cols-4">
  <Card variant="kpi-card">
    <div class="kpi-top"><div><div class="kpi-label">Total scans</div><strong class="kpi">{overview.total_scans || 0}</strong></div><div class="kpi-icon">⇄</div></div>
    <div class="kpi-note">All tracked scan jobs</div>
  </Card>
  <Card variant="kpi-card">
    <div class="kpi-top"><div><div class="kpi-label">Today</div><strong class="kpi">{overview.today_scans || 0}</strong></div><div class="kpi-icon">☀</div></div>
    <div class="kpi-note">Created in the current day</div>
  </Card>
  <Card variant="kpi-card">
    <div class="kpi-top"><div><div class="kpi-label">Success rate</div><strong class="kpi">{success}%</strong></div><div class="kpi-icon">✓</div></div>
    <div class="stat-track"><div class="stat-fill" style={`width:${Math.min(100, Math.max(0, success))}%`}></div></div>
  </Card>
  <Card variant="kpi-card">
    <div class="kpi-top"><div><div class="kpi-label">Avg/day</div><strong class="kpi">{overview.average_scans_per_day || 0}</strong></div><div class="kpi-icon">▰</div></div>
    <div class="kpi-note">Long-term workload trend</div>
  </Card>
</section>

<section class="grid cols-2">
  <Card title="Live queue" subtitle={`${active.length} job${active.length === 1 ? '' : 's'} waiting or running`}>
    {#if active.length === 0}
      <div class="list-row"><div><strong>No active scans</strong><p class="muted small">Everything is calm. Start a new scan when ready.</p></div><Badge tone="success" text="idle" /></div>
    {/if}
    <ul class="clean-list">
      {#each active.slice(0, 5) as job}
        <li class="list-row">
          <div>
            <strong>{job.device_id || job.id}</strong>
            <p class="muted small">{job.target_id || 'No target'} · {job.id}</p>
          </div>
          <Badge tone={statusTone(job.status)} text={job.status} />
        </li>
      {/each}
    </ul>
    {#if active.length > 5}
      <button class="btn ghost top-gap" on:click={() => onNavigate('active-scans')}>Show all queue items</button>
    {/if}
  </Card>

  <Card title="Workflow health" subtitle="Scanners, targets and delivery pipeline">
    <div class="stat-grid">
      <div class="stat-row">
        <div><strong>Scanner readiness</strong><div class="stat-track"><div class="stat-fill" style={`width:${data.devices.length ? (onlineDevices / data.devices.length) * 100 : 0}%`}></div></div></div>
        <Badge tone={onlineDevices ? 'success' : 'warning'} text={`${onlineDevices}/${data.devices.length || 0}`} />
      </div>
      <div class="stat-row">
        <div><strong>Target coverage</strong><div class="stat-track"><div class="stat-fill" style={`width:${data.targets.length ? (enabledTargets / data.targets.length) * 100 : 0}%`}></div></div></div>
        <Badge tone={enabledTargets ? 'success' : 'warning'} text={`${enabledTargets}/${data.targets.length || 0}`} />
      </div>
      <div class="stat-row">
        <div><strong>Delivery success</strong><div class="stat-track"><div class="stat-fill" style={`width:${Math.min(100, Math.max(0, success))}%`}></div></div></div>
        <Badge tone={success >= 90 ? 'success' : success >= 60 ? 'warning' : 'danger'} text={`${success}%`} />
      </div>
    </div>
  </Card>
</section>

<Card title="Recent activity" subtitle="Latest scans and delivery state">
  <div class="table-wrap">
    <table>
      <thead><tr><th>ID</th><th>Status</th><th>Device</th><th>Target</th><th>Created</th></tr></thead>
      <tbody>
        {#if recent.length === 0}<tr><td colspan="5" class="muted">No history yet.</td></tr>{/if}
        {#each recent as item}
          <tr>
            <td class="id-cell">{item.id}</td>
            <td><Badge tone={statusTone(item.status)} text={item.status} /></td>
            <td>{item.device_id || '-'}</td>
            <td>{item.target_id || '-'}</td>
            <td>{item.created_at || '-'}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</Card>
