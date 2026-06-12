<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import StatGrid from '../components/StatGrid.svelte';
  import Icon from '../components/ui/Icon.svelte';
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { statusTone, statusKey, isActive } from '../lib/status';

  export let data;
  export let onNavigate = () => {};
  export let onNotify = () => {};

  let cancelling = {};

  $: overview = data.stats.overview || {};
  $: active = (data.jobs || []).filter((j) => isActive(j.status));
  $: recent = (data.history || []).filter((j) => !isActive(j.status)).slice(0, 5);
  $: devices = data.devices || [];
  $: onlineDevices = devices.filter((d) => d.status === 'online').length;
  $: enabledTargets = (data.targets || []).filter((tg) => tg.enabled !== false).length;
  $: kpiCards = [
    { icon: 'devices', label: $t('scannersOnline'), value: `${onlineDevices}/${devices.length}`, sub: $t('scannersOnlineSub') },
    { icon: 'targets', label: $t('targetsConfigured'), value: enabledTargets, sub: $t('targetsConfiguredSub') },
    { icon: 'bolt', label: $t('scansToday'), value: overview.today_scans || 0, sub: $t('scansTodaySub') },
    { icon: 'stats', label: $t('scansTotal'), value: overview.total_scans || 0, sub: $t('scansTotalSub') }
  ];

  function shortId(id) {
    return String(id || '').slice(0, 8);
  }

  function deviceName(job) {
    const device = devices.find((d) => d.id === job.device_id || d.uri === job.device_id);
    return device?.name || job.device_id || $t('unknown');
  }

  function formatTime(value) {
    if (!value) return '—';
    try {
      return new Date(value.endsWith('Z') || value.includes('+') ? value : `${value}Z`).toLocaleString();
    } catch {
      return value;
    }
  }

  async function cancelJob(id) {
    cancelling = { ...cancelling, [id]: true };
    try {
      await api.cancelJob(id);
      onNotify($t('jobCancelled', { id: shortId(id) }), 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    } finally {
      cancelling = { ...cancelling, [id]: false };
    }
  }
</script>

<Card variant="hero-card">
  <div class="hero-content">
    <div>
      <div class="eyebrow">{$t('appTagline')}</div>
      <h2 class="hero-title">{$t('heroTitle')}</h2>
      <p class="hero-copy">{$t('heroCopy')}</p>
    </div>
    <div class="hero-actions">
      <button class="btn primary" on:click={() => onNavigate('new-scan')}>
        <Icon name="scan" size={16} /> {$t('startScanNow')}
      </button>
      <button class="btn ghost" on:click={() => onNavigate('devices')}>
        <Icon name="devices" size={16} /> {$t('goDevices')}
      </button>
      <button class="btn ghost" on:click={() => onNavigate('targets')}>
        <Icon name="targets" size={16} /> {$t('goTargets')}
      </button>
    </div>
  </div>
</Card>

{#if active.length > 0}
  <Card title={$t('activeScans')} subtitle={$t('activeScansSub', { n: active.length })} variant="active-card">
    <ul class="clean-list">
      {#each active as job (job.id)}
        <li class="list-row">
          <div class="row gap center">
            <span class="pulse-dot" aria-hidden="true"></span>
            <div>
              <strong>{deviceName(job)}</strong>
              <p class="muted small">{job.target_id || '—'} · {shortId(job.id)}</p>
            </div>
          </div>
          <div class="row gap center">
            <Badge tone={statusTone(job.status)} text={$t(statusKey(job.status))} />
            <button class="btn ghost small-btn" disabled={cancelling[job.id]} on:click={() => cancelJob(job.id)}>
              <Icon name="x" size={14} /> {$t('cancelJob')}
            </button>
          </div>
        </li>
      {/each}
    </ul>
  </Card>
{/if}

<StatGrid cards={kpiCards} />

<section class="grid cols-2">
  <Card title={$t('scannerStatus')} subtitle={$t('scannerStatusSub')}>
    {#if devices.length === 0}
      <div class="empty-state">
        <Icon name="devices" size={28} />
        <strong>{$t('noDevicesYet')}</strong>
        <p class="muted small">{$t('noDevicesYetHint')}</p>
        <button class="btn primary" on:click={() => onNavigate('devices')}>{$t('goDevices')}</button>
      </div>
    {:else}
      <ul class="clean-list">
        {#each devices as d (d.id)}
          <li class="list-row">
            <div class="row gap center">
              {#if d.is_favorite}<span class="fav-star" title={$t('favorite')}><Icon name="star" size={14} filled /></span>{/if}
              <div>
                <strong>{d.name}</strong>
                <p class="muted small truncate">{d.model || d.connection_type || d.uri}</p>
              </div>
            </div>
            <Badge tone={statusTone(d.status)} text={$t(statusKey(d.status || 'unknown'))} />
          </li>
        {/each}
      </ul>
    {/if}
  </Card>

  <Card title={$t('recentJobs')} subtitle={$t('recentJobsSub')}>
    {#if recent.length === 0}
      <div class="empty-state">
        <Icon name="history" size={28} />
        <strong>{$t('noHistoryYet')}</strong>
        <p class="muted small">{$t('noHistoryYetHint')}</p>
        <button class="btn primary" on:click={() => onNavigate('new-scan')}>{$t('startScanNow')}</button>
      </div>
    {:else}
      <ul class="clean-list">
        {#each recent as job (job.id)}
          <li class="list-row">
            <div class="row gap center">
              <img
                class="job-thumb"
                src={api.jobThumbnailUrl(job.id)}
                alt={$t('thumbnail')}
                loading="lazy"
                on:error={(e) => (e.target.style.display = 'none')}
              />
              <div>
                <strong>{deviceName(job)}</strong>
                <p class="muted small">{job.target_id || '—'} · {formatTime(job.created_at)}</p>
                {#if job.message}<p class="muted small warn-text">{job.message}</p>{/if}
              </div>
            </div>
            <Badge tone={statusTone(job.status)} text={$t(statusKey(job.status))} />
          </li>
        {/each}
      </ul>
      <button class="btn ghost top-gap" on:click={() => onNavigate('history')}>{$t('history')} →</button>
    {/if}
  </Card>
</section>
