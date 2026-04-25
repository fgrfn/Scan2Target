<script>
  import Card from '../components/ui/Card.svelte';
  export let settings;
  export let onChange = () => {};
</script>

<section class="grid cols-2">
  <Card title="Application settings" subtitle="Grouped by behavior and preferences">
    <label><input type="checkbox" checked={settings.autoRefresh} on:change={(e) => onChange({ autoRefresh: e.target.checked })} /> Auto refresh dashboards</label>
    <label><input type="checkbox" checked={settings.compactTables} on:change={(e) => onChange({ compactTables: e.target.checked })} /> Compact table rows</label>
  </Card>

  <Card title="System info">
    <p class="muted">This redesign keeps API contracts intact and is optimized for desktop and mobile admin usage.</p>
  </Card>
</section>
