<script lang="ts">
  import type { Snippet } from 'svelte';
  import { X } from 'lucide-svelte';

  interface Props {
    open: boolean;
    title: string;
    onClose: () => void;
    children?: Snippet;
    wide?: boolean;
  }

  let { open, title, onClose, children, wide = false }: Props = $props();

  function handleBackdrop(e: MouseEvent) { if (e.target === e.currentTarget) onClose(); }
  function handleKeydown(e: KeyboardEvent) { if (e.key === 'Escape') onClose(); }
</script>

{#if open}
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions a11y_interactive_supports_focus -->
  <div class="backdrop" role="dialog" aria-modal="true" aria-label={title}
       tabindex="-1" onclick={handleBackdrop} onkeydown={handleKeydown}>
    <div class="panel" class:wide style="animation: slideUp 0.15s ease;">
      <div class="modal-header">
        <span class="modal-title">{title}</span>
        <button class="btn btn-ghost btn-icon btn-sm" onclick={onClose} aria-label="Close">
          <X size={15} />
        </button>
      </div>
      <div class="modal-body">
        {@render children?.()}
      </div>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed; inset: 0;
    background: rgba(0,0,0,0.65);
    z-index: 1000;
    display: flex; align-items: center; justify-content: center;
    padding: 20px;
    animation: fadeIn 0.12s ease;
  }

  .panel {
    background: var(--c-surface);
    border: 1px solid var(--c-border-em);
    border-radius: 8px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    width: 100%;
    max-width: 480px;
    max-height: calc(100dvh - 40px);
    display: flex; flex-direction: column;
  }
  .wide { max-width: 660px; }

  .modal-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 16px;
    border-bottom: 1px solid var(--c-border);
    flex-shrink: 0;
  }
  .modal-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--c-text);
  }
  .modal-body {
    padding: 16px;
    overflow-y: auto;
    flex: 1;
  }

  @keyframes fadeIn  { from { opacity: 0; }                           to { opacity: 1; } }
  @keyframes slideUp { from { opacity: 0; transform: translateY(6px);} to { opacity: 1; transform: translateY(0); } }

  @media (max-width: 520px) {
    .backdrop { align-items: flex-end; padding: 0; }
    .panel    { max-width: 100%; border-radius: 8px 8px 0 0; margin-top: auto; }
  }
</style>
