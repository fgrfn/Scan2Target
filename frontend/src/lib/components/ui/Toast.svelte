<script lang="ts">
  import { toastStore } from '$lib/stores/toast.svelte';
  import { CheckCircle2, XCircle, Info, X } from 'lucide-svelte';
</script>

<div class="toast-container" aria-live="polite" aria-atomic="false">
  {#each toastStore.toasts as toast (toast.id)}
    <div class="toast toast-{toast.type}" role="alert">
      <span class="toast-icon toast-icon-{toast.type}">
        {#if toast.type === 'success'}<CheckCircle2 size={13} />
        {:else if toast.type === 'error'}<XCircle size={13} />
        {:else}<Info size={13} />{/if}
      </span>
      <span class="toast-msg">{toast.message}</span>
      <button class="toast-close" onclick={() => toastStore.dismiss(toast.id)} aria-label="Dismiss">
        <X size={12} />
      </button>
    </div>
  {/each}
</div>

<style>
  .toast-container {
    position: fixed; bottom: 20px; right: 20px;
    z-index: 9999;
    display: flex; flex-direction: column; gap: 6px;
    max-width: 340px; width: calc(100vw - 40px);
    pointer-events: none;
  }

  .toast {
    display: flex; align-items: center; gap: 9px;
    padding: 10px 12px;
    border-radius: 6px;
    border: 1px solid var(--c-border-em);
    background: var(--c-surface-2);
    color: var(--c-text);
    font-size: 0.8125rem;
    box-shadow: 0 4px 16px rgba(0,0,0,0.4);
    pointer-events: auto;
    animation: slideFromRight 0.18s ease;
  }

  .toast-success { border-color: rgba(34,197,94,0.25);   background: #0d1a0d; }
  .toast-error   { border-color: rgba(239,68,68,0.25);   background: #1a0d0d; }
  .toast-info    { border-color: rgba(59,130,246,0.25);  background: #0d111a; }

  .toast-icon         { display: flex; align-items: center; flex-shrink: 0; }
  .toast-icon-success { color: #4ade80; }
  .toast-icon-error   { color: #f87171; }
  .toast-icon-info    { color: #60a5fa; }

  .toast-msg   { flex: 1; line-height: 1.4; }
  .toast-close {
    flex-shrink: 0; background: none; border: none;
    color: var(--c-text-3); cursor: pointer;
    display: flex; align-items: center; padding: 2px;
    border-radius: 3px;
  }
  .toast-close:hover { color: var(--c-text-2); }

  @keyframes slideFromRight {
    from { opacity: 0; transform: translateX(12px); }
    to   { opacity: 1; transform: translateX(0); }
  }

  @media (max-width: 768px) {
    .toast-container { bottom: 68px; right: 12px; left: 12px; width: auto; }
  }
</style>
