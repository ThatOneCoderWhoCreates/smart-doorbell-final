// Basic Service Worker to allow PWA Installation
const CACHE_NAME = 'doorbell-pwa-v1';

self.addEventListener('install', (event) => {
    console.log('[Service Worker] Install');
});
self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activate');
});
self.addEventListener('fetch', (event) => {
    // Required by Chrome for PWA installability — pass through.
});
self.addEventListener('push', (event) => {
    console.log('[Service Worker] Push Received.');
    const dataText = event.data ? event.data.text() : 'Activity Detected!';
    const options = {
        body: dataText,
        icon: '/static/favicon.ico',
        badge: '/static/favicon.ico',
        vibrate: [200, 100, 200, 100, 200],
        requireInteraction: true,
        actions: [
            { action: 'view_camera', title: '👀 View Camera' },
            { action: 'call_security', title: '🚨 Call Security' }
        ]
    };
    event.waitUntil(self.registration.showNotification('Smart Doorbell Alert', options));
});
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    if (event.action === 'call_security') {
        event.waitUntil(clients.openWindow('tel:911'));
    } else {
        event.waitUntil(
            clients.matchAll({ type: 'window' }).then((windowClients) => {
                for (let i = 0; i < windowClients.length; i++) {
                    const client = windowClients[i];
                    if ('focus' in client) return client.focus();
                }
                if (clients.openWindow) return clients.openWindow('/');
            })
        );
    }
});
