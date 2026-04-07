<script lang="ts">
  import { toastStore } from '$lib/stores/toast.svelte';

  function iconFor(type: string) {
    if (type === 'success') return '✓';
    if (type === 'error') return '✕';
    return 'ℹ';
  }
</script>

<div class="toast-container" aria-live="polite" aria-atomic="false">
  {#each toastStore.toasts as toast (toast.id)}
    <div class="toast toast-{toast.type}" role="alert">
      <span class="toast-icon">{iconFor(toast.type)}</span>
      <span class="toast-message">{toast.message}</span>
      <button
        class="toast-close"
        onclick={() => toastStore.dismiss(toast.id)}
        aria-label="Dismiss"
      >✕</button>
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
  }

  .toast {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px 14px;
    border-radius: var(--radius-md);
    border: 1px solid transparent;
    box-shadow: var(--shadow-lg);
    font-size: 0.875rem;
    animation: slideIn 0.2s ease;
    background: var(--color-surface-raised);
    color: var(--color-text);
  }

  .toast-success {
    border-color: var(--color-success);
    background: var(--color-success-dim);
  }

  .toast-error {
    border-color: var(--color-error);
    background: var(--color-error-dim);
  }

  .toast-info {
    border-color: var(--color-info);
    background: var(--color-info-dim);
  }

  .toast-icon {
    flex-shrink: 0;
    font-weight: 700;
    font-size: 0.75rem;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 1px;
  }

  .toast-success .toast-icon {
    background: var(--color-success);
    color: #fff;
  }

  .toast-error .toast-icon {
    background: var(--color-error);
    color: #fff;
  }

  .toast-info .toast-icon {
    background: var(--color-info);
    color: #fff;
  }

  .toast-message {
    flex: 1;
    line-height: 1.4;
  }

  .toast-close {
    flex-shrink: 0;
    background: none;
    border: none;
    color: var(--color-text-muted);
    font-size: 0.75rem;
    cursor: pointer;
    padding: 2px;
    border-radius: var(--radius-sm);
    line-height: 1;
    margin-top: 1px;
  }

  .toast-close:hover {
    color: var(--color-text);
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateX(20px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }

  @media (max-width: 768px) {
    .toast-container {
      bottom: 16px;
      right: 16px;
      left: 16px;
      width: auto;
    }
  }
</style>
