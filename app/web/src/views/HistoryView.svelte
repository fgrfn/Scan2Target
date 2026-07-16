<script>
  import Icon from '../components/ui/Icon.svelte';
  import { api } from '../lib/api';
  import { lang } from '../lib/i18n';
  export let data;
  export let onHistory = () => {};
  export let onNotify = () => {};
  let query = '';
  let filter = 'all';
  $: c = $lang === 'de'
    ? { search: 'Scans durchsuchen', all: 'Alle', attention: 'Offen', success: 'Erfolgreich', today: 'Heute', yesterday: 'Gestern', older: 'Älter', empty: 'Keine passenden Scans.', retry: 'Erneut senden', remove: 'Löschen', pages: 'Seiten', unknown: 'Unbenannter Scan' }
    : { search: 'Search scans', all: 'All', attention: 'Attention', success: 'Successful', today: 'Today', yesterday: 'Yesterday', older: 'Older', empty: 'No matching scans.', retry: 'Retry delivery', remove: 'Delete', pages: 'pages', unknown: 'Unnamed scan' };
  $: items = [...(data.jobs || []), ...(data.history || [])].filter((item, index, all) => all.findIndex((candidate) => candidate.id === item.id) === index);
  $: filtered = items.filter((item) => {
    const status = String(item.status || '').toLowerCase();
    const matchesFilter = filter === 'all' || (filter === 'attention' ? ['failed','delivery_failed','running','queued','waiting'].includes(status) : status === 'completed');
    const haystack = `${item.id} ${item.device_id} ${item.target_id} ${item.message} ${item.metadata?.filename_prefix || ''}`.toLowerCase();
    return matchesFilter && haystack.includes(query.trim().toLowerCase());
  }).sort((a, b) => {
    const priority = (value) => ['failed','delivery_failed','running','queued','waiting'].includes(String(value.status).toLowerCase()) ? 1 : 0;
    return priority(b) - priority(a) || new Date(b.created_at || 0) - new Date(a.created_at || 0);
  });
  $: groups = groupItems(filtered);

  function dateOf(item) { const raw = item.created_at || item.updated_at; return raw ? new Date(raw.endsWith?.('Z') || raw.includes?.('+') ? raw : `${raw}Z`) : new Date(0); }
  function groupItems(list) {
    const result = { today: [], yesterday: [], older: [] };
    const now = new Date(); const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()); const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
    list.forEach((item) => { const date = dateOf(item); (date >= today ? result.today : date >= yesterday ? result.yesterday : result.older).push(item); });
    return result;
  }
  function tone(status) { status = String(status).toLowerCase(); return status === 'completed' ? 'success' : ['failed','delivery_failed'].includes(status) ? 'danger' : 'active'; }
  function title(item) { return item.metadata?.filename_prefix || item.metadata?.filename || c.unknown; }
  async function refresh() { onHistory(await api.getHistory()); }
  async function retry(id) { try { await api.retryUpload(id); await refresh(); onNotify(c.retry, 'success'); } catch (error) { onNotify(error.message, 'error'); } }
  async function remove(id) { try { await api.deleteHistoryJob(id); await refresh(); onNotify(c.remove, 'success'); } catch (error) { onNotify(error.message, 'error'); } }
</script>

<div class="history-tools"><div class="search-box"><Icon name="scan" size={17} /><input bind:value={query} placeholder={c.search} /></div><div class="choice-pills compact"><button class:active={filter === 'all'} on:click={() => filter = 'all'}>{c.all}</button><button class:active={filter === 'attention'} on:click={() => filter = 'attention'}>{c.attention}</button><button class:active={filter === 'success'} on:click={() => filter = 'success'}>{c.success}</button></div></div>

{#if !filtered.length}<div class="empty-state"><Icon name="history" size={28} />{c.empty}</div>{/if}
{#each [['today', c.today], ['yesterday', c.yesterday], ['older', c.older]] as group}
  {#if groups[group[0]].length}
    <section class="history-group"><h2>{group[1]}</h2><div class="history-list">
      {#each groups[group[0]] as item (item.id)}
        <article class="history-card"><div class="history-thumb"><img src={api.jobThumbnailUrl(item.id)} alt="" on:error={(event) => event.currentTarget.classList.add('hidden')} /><Icon name="page" size={22} /></div><div class="history-copy"><div><strong>{title(item)}</strong><span class="status-chip {tone(item.status)}">{String(item.status || '').replace('_', ' ')}</span></div><p>{dateOf(item).toLocaleString()} · {item.target_id || '—'}{#if item.metadata?.pages} · {item.metadata.pages} {c.pages}{/if}</p>{#if item.message}<small>{item.message}</small>{/if}</div><div class="history-actions">{#if ['failed','delivery_failed'].includes(String(item.status).toLowerCase())}<button class="btn secondary" on:click={() => retry(item.id)}><Icon name="upload" size={15} />{c.retry}</button>{/if}<button class="icon-button danger-text" title={c.remove} on:click={() => remove(item.id)}><Icon name="trash" size={16} /></button></div></article>
      {/each}
    </div></section>
  {/if}
{/each}
