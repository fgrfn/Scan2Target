<script lang="ts">
  import { page } from '$app/stores';
  import { AlertTriangle } from 'lucide-svelte';
</script>

<div style="min-height:100dvh;display:flex;align-items:center;justify-content:center;background:var(--c-bg);padding:24px;">
  <div style="text-align:center;max-width:420px;">
    <div style="display:inline-flex;align-items:center;justify-content:center;width:56px;height:56px;border-radius:12px;background:var(--c-surface);border:1px solid var(--c-border);margin-bottom:20px;">
      <AlertTriangle size={24} style="color:var(--c-warn);" />
    </div>
    <h1 style="font-size:1.25rem;font-weight:600;color:var(--c-text);margin:0 0 8px;">{$page.status} — {$page.error?.message ?? 'Something went wrong'}</h1>
    <p style="font-size:0.875rem;color:var(--c-text-2);margin:0 0 24px;">An unexpected error occurred. Try refreshing the page.</p>
    <a href="/" style="display:inline-block;padding:8px 20px;background:var(--c-accent);color:#fff;border-radius:6px;font-size:0.875rem;font-weight:500;text-decoration:none;">Go home</a>
  </div>
</div>
