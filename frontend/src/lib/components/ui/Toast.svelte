<script lang="ts">
  import { toastStore } from '$lib/stores/toast.svelte';
  import { CheckCircle2, XCircle, Info, X } from 'lucide-svelte';
</script>

<div class="toast-container" aria-live="polite" aria-atomic="false">
  {#each toastStore.toasts as toast (toast.id)}
    <div class="toast toast-{toast.type}" role="alert" style="animation: slideFromRight 0.2s ease;">
      <div class="toast-icon-wrap toast-icon-{toast.type}">
        {#if toast.type === 'success'}
          <CheckCircle2 size={14} />
        {:else if toast.type === 'error'}
          <XCircle size={14} />
        {:else}
          <Info size={14} />
        {/if}
      </div>
      <span class="toast-message">{toast.message}</span>
      <button class="toast-close" onclick={() => toastStore.dismiss(toast.id)} aria-label="Dismiss">
        <X size={13} />
      </button>
    </div>
  {/each}
</div>

<style>
  .toast-container {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-width: 360px;
    width: calc(100vw - 48px);
    pointer-events: none;
  }

  .toast {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 11px 12px;
    border-radius: 10px;
    border: 1px solid transparent;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    font-size: 0.875rem;
    background: #1a1a22;
    color: #e4e4f0;
    pointer-events: auto;
  }

  .toast-success { border-color: rgba(74,222,128,0.25); background: rgba(20,30,20,0.95); }
  .toast-error   { border-color: rgba(248,113,113,0.25); background: rgba(30,16,16,0.95); }
  .toast-info    { border-color: rgba(96,165,250,0.25);  background: rgba(16,20,32,0.95); }

  .toast-icon-wrap {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .toast-icon-success { color: #4ade80; }
  .toast-icon-error   { color: #f87171; }
  .toast-icon-info    { color: #60a5fa; }

  .toast-message {
    flex: 1;
    line-height: 1.4;
    font-size: 0.875rem;
  }

  .toast-close {
    flex-shrink: 0;
    background: none;
    border: none;
    color: #52525b;
    cursor: pointer;
    padding: 2px;
    border-radius: 4px;
    display: flex;
    align-items: center;
  }
  .toast-close:hover { color: #a1a1aa; }

  @media (max-width: 768px) {
    .toast-container {
      bottom: 72px; /* above bottom nav */
      right: 12px;
      left: 12px;
      width: auto;
    }
  }
</style>
