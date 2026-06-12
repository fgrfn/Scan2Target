const API_BASE = '/api/v1';
const TOKEN_KEY = 'scan2target_token';

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // localStorage unavailable
  }
}

let unauthorizedHandler = null;

export function setUnauthorizedHandler(fn) {
  unauthorizedHandler = fn;
}

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 && !path.startsWith('/auth/')) {
    if (unauthorizedHandler) unauthorizedHandler();
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      detail = data.detail || data.message || detail;
      if (typeof detail !== 'string') detail = JSON.stringify(detail);
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
  // Auth
  login: (username, password) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  }),

  getVersion: () => request('/version'),

  // Devices
  getDevices: () => request('/devices'),
  discoverDevices: () => request('/devices/discover'),
  addDevice: (payload) => request('/devices/add', { method: 'POST', body: JSON.stringify(payload) }),
  removeDevice: (id) => request(`/devices/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  checkDevice: (id) => request(`/devices/${encodeURIComponent(id)}/check`),
  setFavoriteDevice: (id, isFavorite) => request(`/devices/${encodeURIComponent(id)}/favorite`, {
    method: 'POST',
    body: JSON.stringify({ is_favorite: isFavorite })
  }),

  // Targets
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

  // Scanning
  getProfiles: () => request('/scan/profiles'),
  startScan: (payload) => request('/scan/start', { method: 'POST', body: JSON.stringify(payload) }),
  scanPreview: (payload) => request('/scan/preview', { method: 'POST', body: JSON.stringify(payload) }),
  scanPage: (payload) => request('/scan/page', { method: 'POST', body: JSON.stringify(payload) }),
  startBatchScan: (payload) => request('/scan/batch', { method: 'POST', body: JSON.stringify(payload) }),
  getJobs: () => request('/scan/jobs'),
  cancelJob: (id) => request(`/scan/jobs/${encodeURIComponent(id)}/cancel`, { method: 'POST' }),
  jobThumbnailUrl: (id) => `${API_BASE}/scan/jobs/${encodeURIComponent(id)}/thumbnail`,

  // History
  getHistory: () => request('/history'),
  clearHistory: () => request('/history', { method: 'DELETE' }),
  deleteHistoryJob: (id) => request(`/history/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  retryUpload: (id) => request(`/history/${encodeURIComponent(id)}/retry-upload`, { method: 'POST' }),

  // Profile management
  listManagedProfiles: () => request('/profiles/'),
  createProfile: (payload) => request('/profiles/', { method: 'POST', body: JSON.stringify(payload) }),
  updateProfile: (id, payload) => request(`/profiles/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  }),
  deleteProfile: (id) => request(`/profiles/${encodeURIComponent(id)}`, { method: 'DELETE' }),

  // Statistics
  getStatsOverview: () => request('/stats/overview'),
  getStatsTimeline: () => request('/stats/timeline?days=30'),
  getStatsScanners: () => request('/stats/scanners'),
  getStatsTargets: () => request('/stats/targets'),
  getStatsHourly: () => request('/stats/hourly')
};
