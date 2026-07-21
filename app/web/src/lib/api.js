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

async function requestBlob(path) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { headers });
  if (res.status === 401) {
    if (unauthorizedHandler) unauthorizedHandler();
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      // Ignore parse errors
    }
    throw new Error(detail);
  }
  return res.blob();
}

export const api = {
  // Auth
  getSetupStatus: () => request('/auth/setup-status'),
  setup: (username, password, email = null) => request('/auth/setup', {
    method: 'POST',
    body: JSON.stringify({ username, password, email: email || null })
  }),
  login: (username, password) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  getAuthConfig: () => request('/auth/config'),
  getMe: () => request('/auth/me'),
  setAuthConfig: (enabled) => request('/auth/config', {
    method: 'PUT',
    body: JSON.stringify({ enabled })
  }),
  updateAccount: (payload) => request('/auth/account', {
    method: 'PATCH',
    body: JSON.stringify(payload)
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
  capturePages: (payload) => request('/scan/capture-pages', { method: 'POST', body: JSON.stringify(payload) }),
  startBatchScan: (payload) => request('/scan/batch', { method: 'POST', body: JSON.stringify(payload) }),
  listScanSessions: () => request('/scan/sessions'),
  createScanSession: (payload) => request('/scan/sessions', { method: 'POST', body: JSON.stringify(payload) }),
  getScanSession: (id) => request(`/scan/sessions/${encodeURIComponent(id)}`),
  captureScanSession: (id) => request(`/scan/sessions/${encodeURIComponent(id)}/capture`, { method: 'POST' }),
  cancelScanSession: (id) => request(`/scan/sessions/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  removeScanSessionPage: (sessionId, pageId) => request(`/scan/sessions/${encodeURIComponent(sessionId)}/pages/${encodeURIComponent(pageId)}`, { method: 'DELETE' }),
  rotateScanSessionPage: (sessionId, pageId) => request(`/scan/sessions/${encodeURIComponent(sessionId)}/pages/${encodeURIComponent(pageId)}/rotate`, { method: 'POST' }),
  reorderScanSessionPages: (sessionId, pageIds) => request(`/scan/sessions/${encodeURIComponent(sessionId)}/pages`, { method: 'PUT', body: JSON.stringify({ page_ids: pageIds }) }),
  scanSessionPageImage: (sessionId, pageId) => requestBlob(`/scan/sessions/${encodeURIComponent(sessionId)}/pages/${encodeURIComponent(pageId)}/image`),
  finalizeScanSession: (id, payload) => request(`/scan/sessions/${encodeURIComponent(id)}/finalize`, { method: 'POST', body: JSON.stringify(payload) }),
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
