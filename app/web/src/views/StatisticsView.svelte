<script>
  import Card from '../components/ui/Card.svelte';
  export let data;

  $: timeline = [...(data.stats.timeline || [])].reverse();
  $: maxTimeline = Math.max(1, ...timeline.map((d) => d.total || 0));
  $: hourly = data.stats.hourly || [];
  $: maxHourly = Math.max(1, ...hourly.map((d) => d.count || 0));
</script>

<section class="grid cols-2">
  <Card title="Scan timeline (30 days)">
    <div class="bars">
      {#each timeline as day}
        <div class="bar-group" title={`${day.date}: ${day.total}`}>
          <div class="bar" style={`height:${(day.total / maxTimeline) * 100}%`} />
          <small>{day.date.slice(5)}</small>
        </div>
      {/each}
    </div>
  </Card>

  <Card title="Hourly distribution">
    <div class="bars">
      {#each hourly as h}
        <div class="bar-group" title={`${h.hour}:00 → ${h.count}`}>
          <div class="bar info" style={`height:${(h.count / maxHourly) * 100}%`} />
          <small>{h.hour}</small>
        </div>
      {/each}
    </div>
  </Card>
</section>

<section class="grid cols-2 top-gap">
  <Card title="Scanner performance">
    <div class="table-wrap">
      <table><thead><tr><th>Scanner</th><th>Total</th><th>Success %</th></tr></thead>
      <tbody>{#each data.stats.scanners || [] as row}<tr><td>{row.scanner}</td><td>{row.total_scans}</td><td>{row.success_rate}%</td></tr>{/each}</tbody></table>
    </div>
  </Card>

  <Card title="Target performance">
    <div class="table-wrap">
      <table><thead><tr><th>Target</th><th>Deliveries</th><th>Success %</th></tr></thead>
      <tbody>{#each data.stats.targets || [] as row}<tr><td>{row.target}</td><td>{row.total_deliveries}</td><td>{row.success_rate}%</td></tr>{/each}</tbody></table>
    </div>
  </Card>
</section>
