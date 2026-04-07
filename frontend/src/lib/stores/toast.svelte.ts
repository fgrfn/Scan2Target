export type ToastType = 'success' | 'error' | 'info';

export interface ToastMessage {
  id: number;
  message: string;
  type: ToastType;
}

function createToastStore() {
  let toasts = $state<ToastMessage[]>([]);
  let nextId = 0;

  function show(message: string, type: ToastType = 'info', duration = 4000) {
    const id = ++nextId;
    toasts = [...toasts, { id, message, type }];
    setTimeout(() => {
      dismiss(id);
    }, duration);
  }

  function dismiss(id: number) {
    toasts = toasts.filter((t) => t.id !== id);
  }

  return {
    get toasts() {
      return toasts;
    },
    show,
    dismiss
  };
}

export const toastStore = createToastStore();

export function showToast(message: string, type: ToastType = 'info', duration?: number) {
  toastStore.show(message, type, duration);
}
