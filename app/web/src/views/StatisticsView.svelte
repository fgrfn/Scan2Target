<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  export let data;

  $: overview = data.stats.overview || {};
  $: timeline = [...(data.stats.timeline || [])].reverse();
  $: maxTimeline = Math.max(1, ...timeline.map((day) => day.total || 0));
  $: hourly = data.stats.hourly || [];
  $: maxHourly = Math.max(1, ...hourly.map((hour) => hour.count || 0));
</script>

<section class="grid cols-4">
  <div class="metric-card success">
    <span class="metric-label">Total scans</span>
    <strong class="metric-value">{overview.total_scans || 0}</strong>
    <span class="metric-foot">All recorded jobs</span>
  </div>
  <div class="metric-card info">
    <span class="metric-label">Today</span>
    <strong class="metric-value">{overview.today_scans || 0}</strong>
    <span class="metric-foot">Current day volume</span>
  </div>
  <div class="metric-card warning">
    <span class="metric-label">Success</span>
    <strong class="metric-value">{overview.success_rate || 0}%</strong>
    <span class="metric-foot">Delivery reliability</span>
  </div>
  <div class="metric-card">
    <span class="metric-label">Avg/day</span>
    <strong class="metric-value">{overview.average_scans_per_day || 0}</strong>
    <span class="metric-foot">Recent throughput</span>
  </div>
</section>

<section class="grid cols-2">
  <Card title="Scan timeline" subtitle="Last 30 days" eyebrow="Volume">
    {#if timeline.length === 0}
      <div class="empty-state"><div><strong>No timeline data</strong><span>Statistics will appear after scans have been recorded.</span></div></div>
    {:else}
      <div class="bars">
        {#each timeline as day}
          <div class="bar-group" title={`${day.date}: ${day.total}`}>
            <div class="bar" style={`height:${Math.max(4, (day.total / maxTimeline) * 100)}%`} />
            <small>{String(day.date || '').slice(5)}</small>
          </div>
        {/each}
      </div>
    {/if}
  </Card>

  <Card title="Hourly distribution" subtitle="When scans are usually started" eyebrow="Behavior">
    {#if hourly.length === 0}
      <div class="empty-state"><div><strong>No hourly data</strong><span>Hourly distribution is empty.</span></div></div>
    {:else}
      <div class="bars">
        {#each hourly as hour}
          <div class="bar-group" title={`${hour.hour}:00 → ${hour.count}`}>
            <div class="bar info" style={`height:${Math.max(4, (hour.count / maxHourly) * 100)}%`} />
            <small>{hour.hour}</small>
          </div>
        {/each}
      </div>
    {/if}
  </Card>
</section>

<section class="grid cols-2">
  <Card title="Scanner performance" subtitle="Per scanner throughput and success rate" eyebrow="Devices">
    <div class="table-wrap">
      <table>
        <thead><tr><th>Scanner</th><th>Total</th><th>Success</th></tr></thead>
        <tbody>
          {#if !(data.stats.scanners || []).length}<tr><td colspan="3" class="muted">No scanner statistics yet.</td></tr>{/if}
          {#each data.stats.scanners || [] as row}
            <tr><td>{row.scanner}</td><td>{row.total_scans}</td><td><Badge tone="success" text={`${row.success_rate}%`} /></td></tr>
          {/each}
        </tbody>
      </table>
    </div>
  </Card>

  <Card title="Target performance" subtitle="Delivery reliability by destination" eyebrow="Targets">
    <div class="table-wrap">
      <table>
        <thead><tr><th>Target</th><th>Deliveries</th><th>Success</th></tr></thead>
        <tbody>
          {#if !(data.stats.targets || []).length}<tr><td colspan="3" class="muted">No target statistics yet.</td></tr>{/if}
          {#each data.stats.targets || [] as row}
            <tr><td>{row.target}</td><td>{row.total_deliveries}</td><td><Badge tone="success" text={`${row.success_rate}%`} /></td></tr>
          {/each}
        </tbody>
      </table>
    </div>
  </Card>
</section>
