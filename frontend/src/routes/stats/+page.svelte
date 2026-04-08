<script lang="ts">
  import { onMount } from 'svelte';
  import { showToast } from '$lib/stores/toast.svelte';
  import { getOverview, getTimeline, getScannerStats, getTargetStats, getHourlyStats, type StatsOverview, type TimelineEntry, type ScannerStat, type TargetStat, type HourlyEntry } from '$lib/api/stats';
  import Spinner from '$lib/components/ui/Spinner.svelte';
  import { BarChart3, CheckCircle2, XCircle, TrendingUp, Printer, Crosshair, Clock } from 'lucide-svelte';

  let overview = $state<StatsOverview|null>(null); let timeline = $state<TimelineEntry[]>([]);
  let scannerStats = $state<ScannerStat[]>([]); let targetStats = $state<TargetStat[]>([]);
  let hourly = $state<HourlyEntry[]>([]); let loading = $state(true);

  onMount(async()=>{
    try{
      const[ov,tl,sc,tg,hr]=await Promise.all([getOverview(),getTimeline(30),getScannerStats(),getTargetStats(),getHourlyStats()]);
      overview=ov;timeline=tl;scannerStats=sc;targetStats=tg;hourly=hr;
    }catch(e:unknown){showToast(e instanceof Error?e.message:'Failed','error');}
    finally{loading=false;}
  });

  const maxTL  = $derived(timeline.length     ? Math.max(...timeline.map(e=>e.total),1) : 1);
  const maxH   = $derived(hourly.length       ? Math.max(...hourly.map(e=>e.count),1) : 1);
  const maxSC  = $derived(scannerStats.length ? Math.max(...scannerStats.map(s=>s.total),1) : 1);
  const maxTC  = $derived(targetStats.length  ? Math.max(...targetStats.map(t=>t.total),1) : 1);
  const hourlyFull = $derived(Array.from({length:24},(_,h)=>({hour:h,count:hourly.find(e=>e.hour===h)?.count??0})));

  function pct(v:number,m:number){ return m===0?'0%':`${Math.round((v/m)*100)}%`; }
  function fmtDate(ds:string){ return new Date(ds).toLocaleDateString(undefined,{month:'short',day:'numeric'}); }
  function padH(h:number){ return String(h).padStart(2,'0'); }
</script>

<div class="page-wrap">
  <div style="margin-bottom:20px;">
    <h1 class="page-title">Statistics</h1>
    <p class="page-sub">Scan activity overview and trends</p>
  </div>

  {#if loading}
    <div style="display:flex;align-items:center;gap:10px;color:var(--c-text-2);padding:48px 0;"><Spinner /><span>Loading…</span></div>
  {:else}

    <!-- Metric cards -->
    {#if overview}
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px;" class="metrics-grid">

        <div class="card" style="padding:16px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
            <BarChart3 size={14} style="color:var(--c-text-3);" />
            <span style="font-size:0.6875rem;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;color:var(--c-text-2);">Total</span>
          </div>
          <p style="font-size:1.75rem;font-weight:700;color:var(--c-text);line-height:1;">{overview.total}</p>
        </div>

        <div class="card" style="padding:16px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
            <CheckCircle2 size={14} style="color:var(--c-ok);" />
            <span style="font-size:0.6875rem;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;color:var(--c-text-2);">Successful</span>
          </div>
          <p style="font-size:1.75rem;font-weight:700;color:var(--c-ok);line-height:1;">{overview.successful}</p>
        </div>

        <div class="card" style="padding:16px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
            <XCircle size={14} style="color:var(--c-err);" />
            <span style="font-size:0.6875rem;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;color:var(--c-text-2);">Failed</span>
          </div>
          <p style="font-size:1.75rem;font-weight:700;color:var(--c-err);line-height:1;">{overview.failed}</p>
        </div>

        <div class="card" style="padding:16px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
            <TrendingUp size={14} style="color:var(--c-accent);" />
            <span style="font-size:0.6875rem;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;color:var(--c-text-2);">Rate</span>
          </div>
          <p style="font-size:1.75rem;font-weight:700;color:var(--c-accent);line-height:1;">{overview.success_rate.toFixed(1)}<span style="font-size:1rem;">%</span></p>
        </div>
      </div>
    {/if}

    <!-- Charts -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;" class="charts-grid">

      <!-- 30-day timeline -->
      <div class="card" style="padding:16px;">
        <div class="card-header" style="padding:0 0 12px;border-bottom:none;">
          <span class="card-title"><Clock size={13} />Last 30 Days</span>
        </div>
        {#if !timeline.length}
          <div class="empty-state" style="padding:20px;"><p>No data.</p></div>
        {:else}
          <div style="display:flex;flex-direction:column;gap:5px;max-height:280px;overflow-y:auto;">
            {#each timeline as e}
              <div style="display:flex;align-items:center;gap:8px;font-size:0.75rem;">
                <span style="width:46px;text-align:right;color:var(--c-text-3);flex-shrink:0;font-size:0.6875rem;">{fmtDate(e.date)}</span>
                <div style="flex:1;display:flex;flex-direction:column;gap:2px;">
                  <div class="bar-track" style="height:6px;"><div class="bar-fill" style="width:{pct(e.successful,maxTL)};background:var(--c-ok);"></div></div>
                  {#if e.failed>0}<div class="bar-track" style="height:6px;"><div class="bar-fill" style="width:{pct(e.failed,maxTL)};background:var(--c-err);"></div></div>{/if}
                </div>
                <span style="width:24px;text-align:right;color:var(--c-text-2);font-size:0.6875rem;">{e.total}</span>
              </div>
            {/each}
          </div>
          <div style="display:flex;gap:12px;margin-top:10px;font-size:0.6875rem;color:var(--c-text-2);">
            <span style="display:flex;align-items:center;gap:5px;"><span style="width:8px;height:8px;border-radius:1px;display:inline-block;background:var(--c-ok);"></span>OK</span>
            <span style="display:flex;align-items:center;gap:5px;"><span style="width:8px;height:8px;border-radius:1px;display:inline-block;background:var(--c-err);"></span>Failed</span>
          </div>
        {/if}
      </div>

      <!-- Hourly distribution -->
      <div class="card" style="padding:16px;">
        <div class="card-header" style="padding:0 0 12px;border-bottom:none;">
          <span class="card-title"><Clock size={13} />Hourly Distribution</span>
        </div>
        {#if !hourly.length}
          <div class="empty-state" style="padding:20px;"><p>No data.</p></div>
        {:else}
          <div style="display:flex;align-items:flex-end;gap:1px;height:100px;">
            {#each hourlyFull as e}
              <div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;">
                <div style="width:100%;background:var(--c-accent);border-radius:1px 1px 0 0;transition:height 400ms ease;min-height:{e.count>0?'2px':'0'};height:{pct(e.count,maxH)};"
                     title="{padH(e.hour)}:00 — {e.count}"></div>
              </div>
            {/each}
          </div>
          <div style="display:flex;gap:1px;margin-top:4px;">
            {#each hourlyFull as e}
              <div style="flex:1;text-align:center;font-size:0.5rem;color:var(--c-text-3);">{e.hour%6===0?padH(e.hour):''}</div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Top scanners -->
      <div class="card" style="padding:16px;">
        <div class="card-header" style="padding:0 0 12px;border-bottom:none;">
          <span class="card-title"><Printer size={13} />Top Scanners</span>
        </div>
        {#if !scannerStats.length}
          <div class="empty-state" style="padding:20px;"><p>No data.</p></div>
        {:else}
          <div class="bar-chart">
            {#each scannerStats as s}
              <div class="bar-row">
                <span class="bar-label" title={s.device_name}>{s.device_name}</span>
                <div class="bar-track"><div class="bar-fill" style="width:{pct(s.total,maxSC)}"></div></div>
                <span class="bar-val">{s.total}</span>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Top targets -->
      <div class="card" style="padding:16px;">
        <div class="card-header" style="padding:0 0 12px;border-bottom:none;">
          <span class="card-title"><Crosshair size={13} />Top Targets</span>
        </div>
        {#if !targetStats.length}
          <div class="empty-state" style="padding:20px;"><p>No data.</p></div>
        {:else}
          <div class="bar-chart" style="margin-bottom:14px;">
            {#each targetStats as t}
              <div class="bar-row">
                <span class="bar-label" title={t.target_name}>{t.target_name}</span>
                <div class="bar-track"><div class="bar-fill" style="width:{pct(t.total,maxTC)}"></div></div>
                <span class="bar-val">{t.total}</span>
              </div>
            {/each}
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Target</th><th>Type</th><th>Total</th><th>OK</th><th>Fail</th></tr></thead>
              <tbody>
                {#each targetStats as t}
                  <tr>
                    <td>{t.target_name}</td>
                    <td><span class="badge badge-primary">{t.type}</span></td>
                    <td>{t.total}</td>
                    <td style="color:var(--c-ok);">{t.successful}</td>
                    <td style="color:var(--c-err);">{t.total-t.successful}</td>
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
  .metrics-grid { grid-template-columns: repeat(2,1fr) !important; }
  @media (min-width: 640px) { .metrics-grid { grid-template-columns: repeat(4,1fr) !important; } }
  .charts-grid  { grid-template-columns: 1fr !important; }
  @media (min-width: 900px) { .charts-grid { grid-template-columns: 1fr 1fr !important; } }
</style>
