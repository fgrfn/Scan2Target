<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  export let data;

  $: timeline = [...(data.stats.timeline || [])].reverse();
  $: maxTimeline = Math.max(1, ...timeline.map((d) => d.total || 0));
  $: hourly = data.stats.hourly || [];
  $: maxHourly = Math.max(1, ...hourly.map((d) => d.count || 0));
  $: scanners = data.stats.scanners || [];
  $: targets = data.stats.targets || [];
</script>

<section class="grid cols-2">
  <Card title="Scan timeline" subtitle="Last 30 days of scan activity.">
    <div class="bars">
      {#if timeline.length === 0}<p class="muted">No timeline data yet.</p>{/if}
      {#each timeline as day}
        <div class="bar-group" title={`${day.date}: ${day.total}`}>
          <div class="bar" style={`height:${Math.max(3, (day.total / maxTimeline) * 100)}%`}></div>
          <small>{String(day.date || '').slice(5)}</small>
        </div>
      {/each}
    </div>
  </Card>

  <Card title="Hourly distribution" subtitle="When scans are started throughout the day.">
    <div class="bars">
      {#if hourly.length === 0}<p class="muted">No hourly data yet.</p>{/if}
      {#each hourly as h}
        <div class="bar-group" title={`${h.hour}:00 → ${h.count}`}>
          <div class="bar info" style={`height:${Math.max(3, (h.count / maxHourly) * 100)}%`}></div>
          <small>{h.hour}</small>
        </div>
      {/each}
    </div>
  </Card>
</section>

<section class="grid cols-2">
  <Card title="Scanner performance" subtitle="Total scans and success by device.">
    <div class="stat-grid">
      {#if scanners.length === 0}<p class="muted">No scanner performance data yet.</p>{/if}
      {#each scanners as row}
        <div class="stat-row">
          <div>
            <strong>{row.scanner}</strong>
            <div class="stat-track"><div class="stat-fill" style={`width:${Math.min(100, Math.max(0, row.success_rate || 0))}%`}></div></div>
          </div>
          <Badge tone={(row.success_rate || 0) >= 90 ? 'success' : 'warning'} text={`${row.total_scans} · ${row.success_rate}%`} />
        </div>
      {/each}
    </div>
  </Card>

  <Card title="Target performance" subtitle="Delivery success by destination.">
    <div class="stat-grid">
      {#if targets.length === 0}<p class="muted">No target performance data yet.</p>{/if}
      {#each targets as row}
        <div class="stat-row">
          <div>
            <strong>{row.target}</strong>
            <div class="stat-track"><div class="stat-fill" style={`width:${Math.min(100, Math.max(0, row.success_rate || 0))}%`}></div></div>
          </div>
          <Badge tone={(row.success_rate || 0) >= 90 ? 'success' : 'warning'} text={`${row.total_deliveries} · ${row.success_rate}%`} />
        </div>
      {/each}
    </div>
  </Card>
</section>
