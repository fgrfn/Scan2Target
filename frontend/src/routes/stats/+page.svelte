<script lang="ts">
  import { onMount } from 'svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import {
    getOverview, getTimeline, getScannerStats, getTargetStats, getHourlyStats,
    type StatsOverview, type TimelineEntry, type ScannerStat, type TargetStat, type HourlyEntry
  } from '$lib/api/stats';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import { BarChart3, CheckCircle2, XCircle, TrendingUp, Printer, Crosshair, Clock } from 'lucide-svelte';

  let overview     = $state<StatsOverview | null>(null);
  let timeline     = $state<TimelineEntry[]>([]);
  let scannerStats = $state<ScannerStat[]>([]);
  let targetStats  = $state<TargetStat[]>([]);
  let hourly       = $state<HourlyEntry[]>([]);
  let loading      = $state(true);

  onMount(async () => {
    try {
      const [ov, tl, sc, tg, hr] = await Promise.all([
        getOverview(), getTimeline(30), getScannerStats(), getTargetStats(), getHourlyStats()
      ]);
      overview = ov; timeline = tl; scannerStats = sc; targetStats = tg; hourly = hr;
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load stats', 'error');
    } finally { loading = false; }
  });

  const maxTimeline     = $derived(timeline.length     ? Math.max(...timeline.map(e => e.total), 1) : 1);
  const maxHourly       = $derived(hourly.length       ? Math.max(...hourly.map(e => e.count), 1) : 1);
  const maxScannerCount = $derived(scannerStats.length ? Math.max(...scannerStats.map(s => s.total), 1) : 1);
  const maxTargetCount  = $derived(targetStats.length  ? Math.max(...targetStats.map(t => t.total), 1) : 1);

  const hourlyFull = $derived(
    Array.from({ length: 24 }, (_, h) => {
      const found = hourly.find(e => e.hour === h);
      return { hour: h, count: found?.count ?? 0 };
    })
  );

  function pct(val: number, max: number) { return max === 0 ? '0%' : `${Math.round((val/max)*100)}%`; }
  function fmtDate(ds: string) { return new Date(ds).toLocaleDateString(undefined, { month:'short', day:'numeric' }); }
  function padH(h: number) { return String(h).padStart(2,'0'); }
</script>

<div class="page-wrap">
  <div class="mb-6">
    <h1 class="page-title">Statistics</h1>
    <p class="page-sub">Scan activity overview and trends</p>
  </div>

  {#if loading}
    <div class="flex items-center gap-3 text-zinc-500 py-12"><Spinner /><span>Loading…</span></div>
  {:else}

    <!-- Overview metrics -->
    {#if overview}
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <!-- Total -->
        <div class="card p-4">
          <div class="flex items-start justify-between mb-3">
            <div class="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center">
              <BarChart3 size={16} class="text-indigo-400" />
            </div>
          </div>
          <p class="text-2xl font-bold text-zinc-50">{overview.total}</p>
          <p class="text-xs text-zinc-500 mt-0.5 uppercase tracking-wide font-medium">Total Scans</p>
        </div>

        <!-- Successful -->
        <div class="card p-4">
          <div class="flex items-start justify-between mb-3">
            <div class="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
              <CheckCircle2 size={16} class="text-emerald-400" />
            </div>
          </div>
          <p class="text-2xl font-bold text-emerald-400">{overview.successful}</p>
          <p class="text-xs text-zinc-500 mt-0.5 uppercase tracking-wide font-medium">Successful</p>
        </div>

        <!-- Failed -->
        <div class="card p-4">
          <div class="flex items-start justify-between mb-3">
            <div class="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center">
              <XCircle size={16} class="text-red-400" />
            </div>
          </div>
          <p class="text-2xl font-bold text-red-400">{overview.failed}</p>
          <p class="text-xs text-zinc-500 mt-0.5 uppercase tracking-wide font-medium">Failed</p>
        </div>

        <!-- Success rate -->
        <div class="card p-4">
          <div class="flex items-start justify-between mb-3">
            <div class="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center">
              <TrendingUp size={16} class="text-indigo-400" />
            </div>
          </div>
          <p class="text-2xl font-bold text-indigo-400">{overview.success_rate.toFixed(1)}<span class="text-base">%</span></p>
          <p class="text-xs text-zinc-500 mt-0.5 uppercase tracking-wide font-medium">Success Rate</p>
        </div>
      </div>
    {/if}

    <!-- Charts grid -->
    <div class="grid gap-4" style="grid-template-columns: 1fr 1fr;">

      <!-- 30-day timeline -->
      <div class="card p-5 col-span-full lg:col-span-1">
        <div class="flex items-center gap-2 mb-4">
          <span class="card-title flex items-center gap-2">
            <Clock size={14} class="text-zinc-500" /> Last 30 Days
          </span>
        </div>

        {#if timeline.length === 0}
          <div class="empty-state py-6"><p>No data for this period.</p></div>
        {:else}
          <div class="flex flex-col gap-1.5 overflow-y-auto" style="max-height:320px;">
            {#each timeline as entry}
              <div class="flex items-center gap-2" style="font-size:0.75rem;">
                <span class="text-zinc-600 flex-shrink-0 text-right" style="width:52px;">{fmtDate(entry.date)}</span>
                <div class="flex-1 flex flex-col gap-0.5">
                  <div class="bar-track" style="height:8px;">
                    <div class="bar-fill"
                         style="width:{pct(entry.successful,maxTimeline)};background:#4ade80;"></div>
                  </div>
                  {#if entry.failed > 0}
                    <div class="bar-track" style="height:8px;">
                      <div class="bar-fill"
                           style="width:{pct(entry.failed,maxTimeline)};background:#f87171;"></div>
                    </div>
                  {/if}
                </div>
                <span class="text-zinc-500 flex-shrink-0" style="width:28px;text-align:right;">{entry.total}</span>
              </div>
            {/each}
          </div>
          <div class="flex gap-4 mt-3" style="font-size:0.75rem;">
            <span class="flex items-center gap-1.5 text-zinc-500">
              <span class="w-2.5 h-2.5 rounded-sm inline-block" style="background:#4ade80;"></span>Successful
            </span>
            <span class="flex items-center gap-1.5 text-zinc-500">
              <span class="w-2.5 h-2.5 rounded-sm inline-block" style="background:#f87171;"></span>Failed
            </span>
          </div>
        {/if}
      </div>

      <!-- Hourly distribution -->
      <div class="card p-5 col-span-full lg:col-span-1">
        <span class="card-title flex items-center gap-2 mb-4">
          <Clock size={14} class="text-zinc-500" /> Hourly Distribution
        </span>
        {#if hourly.length === 0}
          <div class="empty-state py-6"><p>No hourly data.</p></div>
        {:else}
          <!-- Vertical bar chart -->
          <div class="flex items-end gap-0.5 pt-2" style="height:110px;">
            {#each hourlyFull as entry}
              <div class="flex-1 flex flex-col items-center justify-end h-full">
                <div
                  class="w-full rounded-t transition-all duration-500"
                  style="height:{pct(entry.count,maxHourly)};min-height:{entry.count>0?'3px':'0'};background:rgba(99,102,241,0.6);"
                  title="{padH(entry.hour)}:00 — {entry.count} scan{entry.count!==1?'s':''}"
                ></div>
              </div>
            {/each}
          </div>
          <!-- Hour labels -->
          <div class="flex gap-0.5 mt-1">
            {#each hourlyFull as entry}
              <div class="flex-1 text-center" style="font-size:0.5rem;color:#52525b;">
                {entry.hour % 6 === 0 ? padH(entry.hour) : ''}
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Top scanners -->
      <div class="card p-5">
        <span class="card-title flex items-center gap-2 mb-4">
          <Printer size={14} class="text-zinc-500" /> Top Scanners
        </span>
        {#if scannerStats.length === 0}
          <div class="empty-state py-4"><p>No scanner data.</p></div>
        {:else}
          <div class="bar-chart">
            {#each scannerStats as s}
              <div class="bar-row">
                <span class="bar-label" title={s.device_name}>{s.device_name}</span>
                <div class="bar-track"><div class="bar-fill" style="width:{pct(s.total,maxScannerCount)}"></div></div>
                <span class="bar-val">{s.total}</span>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Top targets -->
      <div class="card p-5">
        <span class="card-title flex items-center gap-2 mb-4">
          <Crosshair size={14} class="text-zinc-500" /> Top Targets
        </span>
        {#if targetStats.length === 0}
          <div class="empty-state py-4"><p>No target data.</p></div>
        {:else}
          <div class="bar-chart">
            {#each targetStats as t}
              <div class="bar-row">
                <span class="bar-label" title={t.target_name}>{t.target_name}</span>
                <div class="bar-track"><div class="bar-fill" style="width:{pct(t.total,maxTargetCount)}"></div></div>
                <span class="bar-val">{t.total}</span>
              </div>
            {/each}
          </div>

          <!-- Details table -->
          <div class="table-wrap mt-5">
            <table>
              <thead>
                <tr>
                  <th>Target</th><th>Type</th><th>Total</th><th>OK</th><th>Fail</th>
                </tr>
              </thead>
              <tbody>
                {#each targetStats as t}
                  <tr>
                    <td class="text-zinc-200">{t.target_name}</td>
                    <td><span class="badge badge-primary">{t.type}</span></td>
                    <td>{t.total}</td>
                    <td class="text-emerald-400">{t.successful}</td>
                    <td class="text-red-400">{t.total - t.successful}</td>
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
  @media (max-width: 768px) {
    .grid { grid-template-columns: 1fr !important; }
  }
</style>
