// Service Worker for Scan2Target PWA
// v3: modern UI refresh; network-first for UI/assets so old builds do not stick.
const CACHE_NAME = 'scan2target-modern-v3';

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => Promise.all(
      cacheNames
        .filter((name) => name !== CACHE_NAME)
        .map((name) => caches.delete(name))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  if (request.url.includes('/api/')) {
    event.respondWith(fetch(request));
    return;
  }

  event.respondWith(
    fetch(request, { cache: 'no-store' })
      .then((response) => {
        const sameOrigin = new URL(request.url).origin === self.location.origin;
        if (sameOrigin && response.ok && request.url.startsWith('http')) {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, responseToCache));
        }
        return response;
      })
      .catch(async () => {
        const cached = await caches.match(request);
        if (cached) return cached;
        if (request.mode === 'navigate') return caches.match('/') || Response.error();
        return Response.error();
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
