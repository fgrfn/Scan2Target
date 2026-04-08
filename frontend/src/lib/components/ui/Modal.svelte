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

  function handleBackdrop(e: MouseEvent) {
    if (e.target === e.currentTarget) onClose();
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
    onclick={handleBackdrop}
    onkeydown={handleKeydown}
  >
    <div class="modal-panel" class:modal-wide={wide} style="animation: scaleIn 0.18s cubic-bezier(0.34,1.56,0.64,1);">
      <!-- Header -->
      <div class="flex items-center justify-between px-5 py-4 border-b border-zinc-800/80 flex-shrink-0">
        <h3 class="text-sm font-semibold text-zinc-100">{title}</h3>
        <button class="btn btn-ghost btn-icon btn-sm text-zinc-500 hover:text-zinc-100"
                onclick={onClose} aria-label="Close">
          <X size={16} />
        </button>
      </div>
      <!-- Body -->
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
    background: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(4px);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    animation: fadeIn 0.15s ease;
  }

  .modal-panel {
    background: #111118;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px;
    box-shadow: 0 24px 64px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.04);
    width: 100%;
    max-width: 480px;
    max-height: calc(100dvh - 40px);
    display: flex;
    flex-direction: column;
  }

  .modal-wide { max-width: 660px; }

  .modal-body {
    padding: 20px;
    overflow-y: auto;
    flex: 1;
  }

  @keyframes fadeIn  { from { opacity: 0; } to { opacity: 1; } }
  @keyframes scaleIn { from { opacity: 0; transform: scale(0.92) translateY(8px); } to { opacity: 1; transform: scale(1) translateY(0); } }

  @media (max-width: 520px) {
    .modal-panel { max-width: 100%; border-radius: 14px 14px 0 0; margin-top: auto; }
    .modal-backdrop { align-items: flex-end; padding: 0; }
  }
</style>
