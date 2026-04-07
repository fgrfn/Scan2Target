<script lang="ts">
  import { onMount } from 'svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import {
    getOverview,
    getTimeline,
    getScannerStats,
    getTargetStats,
    getHourlyStats,
    type StatsOverview,
    type TimelineEntry,
    type ScannerStat,
    type TargetStat,
    type HourlyEntry
  } from '$lib/api/stats';
  import Spinner from '$lib/components/ui/Spinner.svelte';

  let overview = $state<StatsOverview | null>(null);
  let timeline = $state<TimelineEntry[]>([]);
  let scannerStats = $state<ScannerStat[]>([]);
  let targetStats = $state<TargetStat[]>([]);
  let hourly = $state<HourlyEntry[]>([]);
  let loading = $state(true);

  onMount(async () => {
    try {
      const [ov, tl, sc, tg, hr] = await Promise.all([
        getOverview(),
        getTimeline(30),
        getScannerStats(),
        getTargetStats(),
        getHourlyStats()
      ]);
      overview = ov;
      timeline = tl;
      scannerStats = sc;
      targetStats = tg;
      hourly = hr;
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load stats', 'error');
    } finally {
      loading = false;
    }
  });

  const maxTimeline = $derived(
    timeline.length ? Math.max(...timeline.map((e) => e.total), 1) : 1
  );

  const maxHourly = $derived(
    hourly.length ? Math.max(...hourly.map((e) => e.count), 1) : 1
  );

  const maxScannerCount = $derived(
    scannerStats.length ? Math.max(...scannerStats.map((s) => s.total), 1) : 1
  );

  const maxTargetCount = $derived(
    targetStats.length ? Math.max(...targetStats.map((t) => t.total), 1) : 1
  );

  function pct(value: number, max: number): string {
    if (max === 0) return '0%';
    return `${Math.round((value / max) * 100)}%`;
  }

  function formatDate(ds: string): string {
    return new Date(ds).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }

  function padHour(h: number): string {
    return String(h).padStart(2, '0') + ':00';
  }

  // Build full 24-hour array for hourly chart
  const hourlyFull = $derived(
    Array.from({ length: 24 }, (_, h) => {
      const found = hourly.find((e) => e.hour === h);
      return { hour: h, count: found?.count ?? 0 };
    })
  );
</script>

<div class="page-header">
  <h1 class="page-title">📊 Statistics</h1>
  <p class="page-subtitle">Scan activity overview and trends</p>
</div>

<div class="page-body">
  {#if loading}
    <div class="flex items-center gap-3">
      <Spinner />
      <span class="text-muted">Loading…</span>
    </div>
  {:else}
    <!-- Overview cards -->
    {#if overview}
      <div class="overview-grid mb-6">
        <div class="stat-card">
          <span class="stat-label">Total Scans</span>
          <span class="stat-value">{overview.total}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Successful</span>
          <span class="stat-value text-success">{overview.successful}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Failed</span>
          <span class="stat-value text-error">{overview.failed}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Success Rate</span>
          <span class="stat-value text-primary">{overview.success_rate.toFixed(1)}%</span>
        </div>
      </div>
    {/if}

    <div class="stats-layout">
      <!-- Timeline -->
      <div class="card">
        <h2 class="card-title">📅 Last 30 Days</h2>
        {#if timeline.length === 0}
          <div class="empty-state"><p>No data for this period.</p></div>
        {:else}
          <div class="bar-chart timeline-chart">
            {#each timeline as entry}
              <div class="bar-row timeline-row">
                <span class="bar-label" style="width:64px;font-size:0.7rem">{formatDate(entry.date)}</span>
                <div class="timeline-bars">
                  <div class="bar-track" style="flex:1">
                    <div
                      class="bar-fill"
                      style="width:{pct(entry.successful, maxTimeline)};background:var(--color-success)"
                    ></div>
                  </div>
                  {#if entry.failed > 0}
                    <div class="bar-track" style="flex:1">
                      <div
                        class="bar-fill"
                        style="width:{pct(entry.failed, maxTimeline)};background:var(--color-error)"
                      ></div>
                    </div>
                  {/if}
                </div>
                <span class="bar-value">{entry.total}</span>
              </div>
            {/each}
          </div>
          <div class="legend">
            <span class="legend-item"><span class="legend-dot" style="background:var(--color-success)"></span>Successful</span>
            <span class="legend-item"><span class="legend-dot" style="background:var(--color-error)"></span>Failed</span>
          </div>
        {/if}
      </div>

      <!-- Hourly distribution -->
      <div class="card">
        <h2 class="card-title">🕐 Hourly Distribution</h2>
        {#if hourly.length === 0}
          <div class="empty-state"><p>No hourly data available.</p></div>
        {:else}
          <div class="hourly-chart">
            {#each hourlyFull as entry}
              <div class="hourly-col">
                <div class="hourly-bar-wrap">
                  <div
                    class="hourly-bar"
                    style="height:{pct(entry.count, maxHourly)}"
                    title="{padHour(entry.hour)}: {entry.count} scan{entry.count !== 1 ? 's' : ''}"
                  ></div>
                </div>
                {#if entry.hour % 6 === 0}
                  <span class="hourly-label">{padHour(entry.hour)}</span>
                {:else}
                  <span class="hourly-label"></span>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Scanner stats -->
      <div class="card">
        <h2 class="card-title">📡 Top Scanners</h2>
        {#if scannerStats.length === 0}
          <div class="empty-state"><p>No scanner data.</p></div>
        {:else}
          <div class="bar-chart">
            {#each scannerStats as s}
              <div class="bar-row">
                <span class="bar-label" title={s.device_name}>{s.device_name}</span>
                <div class="bar-track">
                  <div class="bar-fill" style="width:{pct(s.total, maxScannerCount)}"></div>
                </div>
                <span class="bar-value">{s.total}</span>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Target stats -->
      <div class="card">
        <h2 class="card-title">🎯 Top Targets</h2>
        {#if targetStats.length === 0}
          <div class="empty-state"><p>No target data.</p></div>
        {:else}
          <div class="bar-chart">
            {#each targetStats as t}
              <div class="bar-row">
                <span class="bar-label" title={t.target_name}>{t.target_name}</span>
                <div class="bar-track">
                  <div class="bar-fill" style="width:{pct(t.total, maxTargetCount)}"></div>
                </div>
                <span class="bar-value">{t.total}</span>
              </div>
            {/each}
          </div>

          <div class="table-wrap" style="margin-top:20px">
            <table>
              <thead>
                <tr>
                  <th>Target</th>
                  <th>Type</th>
                  <th>Total</th>
                  <th>Successful</th>
                  <th>Failed</th>
                </tr>
              </thead>
              <tbody>
                {#each targetStats as t}
                  <tr>
                    <td>{t.target_name}</td>
                    <td><span class="badge badge-primary">{t.type}</span></td>
                    <td>{t.total}</td>
                    <td class="text-success">{t.successful}</td>
                    <td class="text-error">{t.total - t.successful}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .overview-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 16px;
  }

  .stats-layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
  }

  @media (max-width: 900px) {
    .stats-layout {
      grid-template-columns: 1fr;
    }
  }

  .timeline-chart {
    max-height: 320px;
    overflow-y: auto;
  }

  .timeline-row {
    align-items: center;
  }

  .timeline-bars {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .timeline-bars .bar-track {
    height: 8px;
  }

  .legend {
    display: flex;
    gap: 16px;
    margin-top: 12px;
    font-size: 0.78rem;
    color: var(--color-text-muted);
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .legend-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 2px;
  }

  /* Hourly bar chart */
  .hourly-chart {
    display: flex;
    align-items: flex-end;
    gap: 2px;
    height: 120px;
    padding-bottom: 20px;
    position: relative;
  }

  .hourly-col {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
    position: relative;
  }

  .hourly-bar-wrap {
    flex: 1;
    width: 100%;
    display: flex;
    align-items: flex-end;
    justify-content: center;
  }

  .hourly-bar {
    width: 100%;
    background: var(--color-primary);
    border-radius: 2px 2px 0 0;
    min-height: 2px;
    transition: height 0.4s ease;
  }

  .hourly-label {
    font-size: 0.6rem;
    color: var(--color-text-dim);
    position: absolute;
    bottom: 0;
    white-space: nowrap;
    transform: rotate(-35deg);
    transform-origin: top left;
    left: 0;
  }
</style>
