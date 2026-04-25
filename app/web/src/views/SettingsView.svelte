<script>
  import Card from '../components/ui/Card.svelte';
  import Badge from '../components/ui/Badge.svelte';
  export let settings;
  export let version = '';
  export let lastUpdated = null;
  export let onChange = () => {};

  $: updatedText = lastUpdated ? new Date(lastUpdated).toLocaleString() : 'Not synced yet';
</script>

<section class="grid cols-2">
  <Card title="Interface behavior" subtitle="Small preferences for daily operation.">
    <label class="checkbox-line"><input type="checkbox" checked={settings.autoRefresh} on:change={(e) => onChange({ autoRefresh: e.target.checked })} /> Auto refresh dashboards every 10 seconds</label>
    <label class="checkbox-line"><input type="checkbox" checked={settings.compactTables} on:change={(e) => onChange({ compactTables: e.target.checked })} /> Compact table rows</label>
    <label class="checkbox-line"><input type="checkbox" checked={settings.glassEffects} on:change={(e) => onChange({ glassEffects: e.target.checked })} /> Modern glass effects</label>
  </Card>

  <Card title="System info" subtitle="Frontend and backend status.">
    <div class="resource-meta">
      <div class="meta-box"><span>Version</span><strong>{version || 'unknown'}</strong></div>
      <div class="meta-box"><span>Last update</span><strong>{updatedText}</strong></div>
      <div class="meta-box"><span>UI package</span><strong>Modern Command Center</strong></div>
      <div class="meta-box"><span>Cache strategy</span><strong>Network-first</strong></div>
    </div>
    <div class="top-gap"><Badge tone="success" text="redesigned" /></div>
  </Card>
</section>
