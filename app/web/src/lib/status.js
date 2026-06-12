// Single source of truth for mapping job/device statuses to badge tones.
export function statusTone(status) {
  const s = String(status || '').toLowerCase();
  if (s === 'completed' || s === 'online') return 'success';
  if (s === 'failed' || s === 'offline' || s === 'error') return 'danger';
  if (s === 'running' || s === 'queued' || s === 'waiting') return 'warning';
  if (s === 'cancelled') return 'neutral';
  return 'info';
}

export const ACTIVE_STATUSES = ['queued', 'running', 'waiting'];

export function isActive(status) {
  return ACTIVE_STATUSES.includes(String(status || '').toLowerCase());
}

export function statusKey(status) {
  return `status_${String(status || 'unknown').toLowerCase()}`;
}
