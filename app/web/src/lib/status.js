// Single source of truth for mapping job/device statuses to badge tones.
export function statusTone(status) {
  const s = String(status || '').toLowerCase();
  if (s === 'completed' || s === 'online') return 'success';
  if (s === 'failed' || s === 'delivery_failed' || s === 'offline' || s === 'error') return 'danger';
  if (ACTIVE_STATUSES.includes(s)) return 'warning';
  if (s === 'cancelled') return 'neutral';
  return 'info';
}

export const ACTIVE_STATUSES = [
  'queued',
  'running',
  'waiting',
  'scanning',
  'processing',
  'delivering',
  'retry_scheduled'
];

export function isActive(status) {
  return ACTIVE_STATUSES.includes(String(status || '').toLowerCase());
}

export function statusKey(status) {
  return `status_${String(status || 'unknown').toLowerCase()}`;
}
