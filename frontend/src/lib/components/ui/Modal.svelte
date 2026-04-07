<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    open: boolean;
    title: string;
    onClose: () => void;
    children?: Snippet;
    wide?: boolean;
  }

  let { open, title, onClose, children, wide = false }: Props = $props();

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) {
      onClose();
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') onClose();
  }
</script>

{#if open}
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions a11y_interactive_supports_focus -->
  <div
    class="modal-backdrop"
    role="dialog"
    aria-modal="true"
    aria-label={title}
    tabindex="-1"
    onclick={handleBackdropClick}
    onkeydown={handleKeydown}
  >
    <div class="modal-panel" class:modal-wide={wide}>
      <div class="modal-header">
        <h3 class="modal-title">{title}</h3>
        <button class="modal-close btn btn-ghost btn-icon" onclick={onClose} aria-label="Close">
          ✕
        </button>
      </div>
      <div class="modal-body">
        {@render children?.()}
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.65);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    animation: fadeIn 0.15s ease;
  }

  .modal-panel {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
    width: 100%;
    max-width: 480px;
    max-height: calc(100vh - 40px);
    display: flex;
    flex-direction: column;
    animation: scaleIn 0.15s ease;
  }

  .modal-wide {
    max-width: 680px;
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 20px 16px;
    border-bottom: 1px solid var(--color-border);
    flex-shrink: 0;
  }

  .modal-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--color-text);
  }

  .modal-close {
    color: var(--color-text-muted);
    font-size: 0.875rem;
  }

  .modal-body {
    padding: 20px;
    overflow-y: auto;
    flex: 1;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes scaleIn {
    from { opacity: 0; transform: scale(0.95); }
    to { opacity: 1; transform: scale(1); }
  }
</style>
