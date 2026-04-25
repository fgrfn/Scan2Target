// Scan2Target service worker
// v3: force fresh UI after full redesign and keep offline fallback best-effort only.
const CACHE_NAME = 'scan2target-v3-command-center';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => Promise.all(cacheNames.map((name) => caches.delete(name))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(request));
    return;
  }

  event.respondWith(
    fetch(request, { cache: 'no-store' })
      .then((response) => {
        if (response.ok && request.mode === 'navigate') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put('/', clone));
        }
        return response;
      })
      .catch(async () => {
        if (request.mode === 'navigate') {
          const cachedIndex = await caches.match('/');
          if (cachedIndex) return cachedIndex;
        }
        const cached = await caches.match(request);
        if (cached) return cached;
        throw new Error('Network error and no cache fallback available');
      })
  );
});

self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'Scan2Target';
  const options = {
    body: data.body || 'Scan completed',
    icon: '/icon-192.png',
    badge: '/icon-96.png',
    data,
    actions: [
      { action: 'view', title: 'View' },
      { action: 'close', title: 'Close' }
    ]
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'view') event.waitUntil(clients.openWindow('/#history'));
});
