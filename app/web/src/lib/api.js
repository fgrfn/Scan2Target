const API_BASE = '/api/v1';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      detail = data.detail || data.message || detail;
    } catch {
      // Ignore parse errors
    }
    throw new Error(detail);
  }

  if (res.status === 204) return null;
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

export const api = {
  getVersion: () => request('/version'),
  getDevices: () => request('/devices'),
  discoverDevices: () => request('/devices/discover'),
  addDevice: (payload) => request('/devices/add', { method: 'POST', body: JSON.stringify(payload) }),
  removeDevice: (id) => request(`/devices/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  checkDevice: (id) => request(`/devices/${encodeURIComponent(id)}/check`),
  setFavoriteDevice: (id, isFavorite) => request(`/devices/${encodeURIComponent(id)}/favorite`, {
    method: 'POST',
    body: JSON.stringify({ is_favorite: isFavorite })
  }),

  getTargets: () => request('/targets'),
  createTarget: (payload, validate = true) => request(`/targets?validate=${validate}`, {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  updateTarget: (id, payload, validate = true) => request(`/targets/${encodeURIComponent(id)}?validate=${validate}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  }),
  deleteTarget: (id) => request(`/targets/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  testTarget: (id) => request(`/targets/${encodeURIComponent(id)}/test`, { method: 'POST' }),

  getProfiles: () => request('/scan/profiles'),
  startScan: (payload) => request('/scan/start', { method: 'POST', body: JSON.stringify(payload) }),
  getJobs: () => request('/scan/jobs'),
  cancelJob: (id) => request(`/scan/jobs/${encodeURIComponent(id)}/cancel`, { method: 'POST' }),

  getHistory: () => request('/history'),
  clearHistory: () => request('/history', { method: 'DELETE' }),
  deleteHistoryJob: (id) => request(`/history/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  retryUpload: (id) => request(`/history/${encodeURIComponent(id)}/retry-upload`, { method: 'POST' }),

  getStatsOverview: () => request('/stats/overview'),
  getStatsTimeline: () => request('/stats/timeline?days=30'),
  getStatsScanners: () => request('/stats/scanners'),
  getStatsTargets: () => request('/stats/targets'),
  getStatsHourly: () => request('/stats/hourly')
};
