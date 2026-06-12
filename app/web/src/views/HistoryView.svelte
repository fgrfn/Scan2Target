<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import StatGrid from '../components/StatGrid.svelte';
  import Icon from '../components/ui/Icon.svelte';
  import { api } from '../lib/api';
  import { t } from '../lib/i18n';
  import { statusTone, statusKey } from '../lib/status';

  export let data;
  export let onHistory = () => {};
  export let onNotify = () => {};

  let query = '';
  let status = 'all';

  $: history = data.history || [];
  $: filtered = history.filter((item) => {
    const q = query.trim().toLowerCase();
    const matchQuery =
      !q ||
      String(item.id || '').toLowerCase().includes(q) ||
      String(item.device_id || '').toLowerCase().includes(q) ||
      String(item.target_id || '').toLowerCase().includes(q) ||
      String(item.message || '').toLowerCase().includes(q);
    const matchStatus = status === 'all' || item.status === status;
    return matchQuery && matchStatus;
  });
  $: kpiCards = [
    { icon: 'history', label: $t('recordsTotal'), value: history.length, sub: $t('recordsTotalSub') },
    { icon: 'check', label: $t('completedCount'), value: history.filter((i) => i.status === 'completed').length, sub: $t('completedCountSub') },
    { icon: 'alert', label: $t('failedCount'), value: history.filter((i) => i.status === 'failed').length, sub: $t('failedCountSub') },
    { icon: 'page', label: $t('filteredCount'), value: filtered.length, sub: $t('filteredCountSub') }
  ];

  function shortId(id) {
    return String(id || '').slice(0, 8);
  }

  function formatTime(value) {
    if (!value) return '—';
    try {
      return new Date(value.endsWith('Z') || value.includes('+') ? value : `${value}Z`).toLocaleString();
    } catch {
      return value;
    }
  }

  function canRetry(item) {
    return item.status === 'failed' || (item.message || '').toLowerCase().includes('upload failed');
  }

  async function refresh() {
    onHistory(await api.getHistory());
  }

  async function clearCompleted() {
    try {
      await api.clearHistory();
      await refresh();
      onNotify($t('historyCleared'), 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function del(id) {
    try {
      await api.deleteHistoryJob(id);
      await refresh();
      onNotify($t('deletedRecord', { id: shortId(id) }), 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }

  async function retry(id) {
    try {
      await api.retryUpload(id);
      await refresh();
      onNotify($t('retryRequested', { id: shortId(id) }), 'success');
    } catch (error) {
      onNotify(error.message, 'error');
    }
  }
</script>

<StatGrid cards={kpiCards} />

<Card title={$t('historyTitle')} subtitle={$t('historySub')}>
  <div class="row gap wrap">
    <input class="search" bind:value={query} placeholder={$t('searchPlaceholder')} />
    <select bind:value={status}>
      <option value="all">{$t('allStatuses')}</option>
      {#each ['completed', 'failed', 'running', 'queued', 'cancelled'] as s}
        <option value={s}>{$t(`status_${s}`)}</option>
      {/each}
    </select>
    <button class="btn ghost" on:click={refresh}><Icon name="refresh" size={14} /> {$t('refreshData')}</button>
    <button class="btn danger" on:click={clearCompleted}><Icon name="trash" size={14} /> {$t('clearCompleted')}</button>
  </div>

  <div class="table-wrap top-gap">
    <table>
      <thead>
        <tr>
          <th>{$t('thumbnail')}</th>
          <th>{$t('idLabel')}</th>
          <th>Status</th>
          <th>{$t('device')}</th>
          <th>{$t('target')}</th>
          <th>{$t('created')}</th>
          <th>{$t('actions')}</th>
        </tr>
      </thead>
      <tbody>
        {#if filtered.length === 0}
          <tr><td colspan="7" class="muted">{$t('noRecords')}</td></tr>
        {/if}
        {#each filtered as item (item.id)}
          <tr>
            <td>
              <img
                class="job-thumb"
                src={api.jobThumbnailUrl(item.id)}
                alt={$t('thumbnail')}
                loading="lazy"
                on:error={(e) => (e.target.style.display = 'none')}
              />
            </td>
            <td class="id-cell" title={item.id}>{shortId(item.id)}</td>
            <td>
              <Badge tone={statusTone(item.status)} text={$t(statusKey(item.status))} />
              {#if item.message}<p class="muted small warn-text">{item.message}</p>{/if}
            </td>
            <td class="truncate">{item.device_id || '—'}</td>
            <td>{item.target_id || '—'}</td>
            <td>{formatTime(item.created_at)}</td>
            <td>
              <div class="row gap">
                {#if canRetry(item)}
                  <button class="btn ghost small-btn" on:click={() => retry(item.id)}>
                    <Icon name="upload" size={14} /> {$t('retryUpload')}
                  </button>
                {/if}
                <button class="btn danger small-btn" on:click={() => del(item.id)}>
                  <Icon name="trash" size={14} />
                </button>
              </div>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</Card>
