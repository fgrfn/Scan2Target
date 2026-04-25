<script>
  import Card from '../components/ui/Card.svelte';
  export let settings;
  export let onChange = () => {};
</script>

<section class="grid cols-2">
  <Card title="Application settings" subtitle="Behavior and UI preferences" eyebrow="Preferences">
    <div class="form-grid">
      <label class="check-field"><input type="checkbox" checked={settings.autoRefresh} on:change={(event) => onChange({ autoRefresh: event.target.checked })} /> Auto refresh dashboards every 10 seconds</label>
      <label class="check-field"><input type="checkbox" checked={settings.compactTables} on:change={(event) => onChange({ compactTables: event.target.checked })} /> Compact table rows</label>
    </div>
  </Card>

  <Card title="System info" subtitle="Deployment hints" eyebrow="Scan2Target">
    <div class="list-stack">
      <div class="list-row">
        <div class="list-main"><strong>Frontend</strong><span>Svelte + Vite, responsive PWA shell</span></div>
      </div>
      <div class="list-row">
        <div class="list-main"><strong>API</strong><span>Existing /api/v1 contracts are unchanged</span></div>
      </div>
      <div class="list-row">
        <div class="list-main"><strong>Cache</strong><span>Service worker is network-first to avoid stale UI</span></div>
      </div>
    </div>
  </Card>
</section>

<Card title="Redesign notes" subtitle="What changed visually" eyebrow="UI">
  <div class="grid cols-3">
    <div class="review-item"><span>Navigation</span><strong>Desktop sidebar + mobile dock</strong></div>
    <div class="review-item"><span>Dashboard</span><strong>Hero, metrics and live queue</strong></div>
    <div class="review-item"><span>Workflow</span><strong>Guided scan wizard</strong></div>
  </div>
</Card>
