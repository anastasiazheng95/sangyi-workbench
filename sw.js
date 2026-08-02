// 网络优先、不缓存任何内容，保证永远拉取最新页面与数据。
// 配合 index.html 中的 getRegistrations().unregister()，页面加载一次后即彻底移除 SW。
const CACHE = 'sangyi-pwa-v5';
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(
  caches.keys()
    .then(keys => Promise.all(keys.map(k => caches.delete(k))))
    .then(() => self.clients.claim())
));
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request).catch(() => {
      if (e.request.mode === 'navigate') return caches.match('./index.html');
      return new Response('', { status: 504 });
    })
  );
});
