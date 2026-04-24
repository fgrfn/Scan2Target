// Service Worker for Progressive Web App (PWA)
// v2: avoid pinning stale /index.html or hashed assets across redesign deployments
const CACHE_NAME = 'scan2target-v2';

self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
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

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Always bypass cache for API traffic
  if (request.url.includes('/api/')) {
    event.respondWith(fetch(request));
    return;
  }

  // Network-first for UI/assets to make sure newest redesign is shown.
  event.respondWith(
    fetch(request)
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

        // Fallback to app shell when offline navigation is requested
        if (request.mode === 'navigate') {
          const cachedIndex = await caches.match('/');
          if (cachedIndex) return cachedIndex;
        }

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

  if (event.action === 'view') {
    event.waitUntil(clients.openWindow('/#history'));
  }
});
