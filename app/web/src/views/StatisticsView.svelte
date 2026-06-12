<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import { t } from '../lib/i18n';

  export let data;

  $: timeline = [...(data.stats.timeline || [])].reverse();
  $: maxTimeline = Math.max(1, ...timeline.map((d) => d.total || 0));
  $: hourly = data.stats.hourly || [];
  $: maxHourly = Math.max(1, ...hourly.map((d) => d.count || 0));
  $: scanners = data.stats.scanners || [];
  $: targets = data.stats.targets || [];
</script>

<section class="grid cols-2">
  <Card title={$t('timelineTitle')} subtitle={$t('timelineSub')}>
    <div class="bars">
      {#if timeline.length === 0}<p class="muted">{$t('noTimelineData')}</p>{/if}
      {#each timeline as day}
        <div class="bar-group" title={`${day.date}: ${day.total}`}>
          <div class="bar" style={`height:${Math.max(3, (day.total / maxTimeline) * 100)}%`}></div>
          <small>{String(day.date || '').slice(5)}</small>
        </div>
      {/each}
    </div>
  </Card>

  <Card title={$t('hourlyTitle')} subtitle={$t('hourlySub')}>
    <div class="bars">
      {#if hourly.length === 0}<p class="muted">{$t('noHourlyData')}</p>{/if}
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
  <Card title={$t('scannerPerf')} subtitle={$t('scannerPerfSub')}>
    <div class="stat-grid">
      {#if scanners.length === 0}<p class="muted">{$t('noScannerPerf')}</p>{/if}
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

  <Card title={$t('targetPerf')} subtitle={$t('targetPerfSub')}>
    <div class="stat-grid">
      {#if targets.length === 0}<p class="muted">{$t('noTargetPerf')}</p>{/if}
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
