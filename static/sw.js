/* Service Worker do Estoque Cozinha (PWA + Web Push) */
const CACHE_NAME = 'estoque-v1';
const OFFLINE_URL = '/offline/';

const PRECACHE_URLS = [
  '/',
  '/static/css/app.css',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

// ===== Install: pré-cache de recursos críticos
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

// ===== Activate: limpa caches antigos
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

// ===== Fetch: network-first com fallback cache
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.startsWith('/admin/')) return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then(cache => {
          if (event.request.url.startsWith(self.location.origin)) {
            cache.put(event.request, copy);
          }
        });
        return response;
      })
      .catch(() => caches.match(event.request).then(r => r || caches.match('/')))
  );
});

// ===== Push: notificação quando o servidor envia
self.addEventListener('push', event => {
  let data = { title: 'Estoque Cozinha', body: 'Você tem uma nova notificação.', url: '/' };
  try {
    if (event.data) data = event.data.json();
  } catch (e) {
    if (event.data) data.body = event.data.text();
  }
  const options = {
    body: data.body,
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-192.png',
    tag: data.tag || 'estoque',
    data: { url: data.url || '/' },
    vibrate: [100, 50, 100],
    requireInteraction: false,
  };
  event.waitUntil(self.registration.showNotification(data.title, options));
});

// ===== Notification click: abre a URL
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(list => {
      for (const client of list) {
        if (client.url.includes(url) && 'focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
