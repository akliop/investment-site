// sw.js - الخدمة المضافة للحفاظ على نشاط الموقع ومنع خمول الأجهزة
self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
    // ترك الطلبات تمر بشكل طبيعي
});

// ميزة التنبيه لإبقاء الجهاز يقظاً قدر الإمكان
self.addEventListener('push', (event) => {
    const data = event.data.json();
    self.registration.showNotification(data.title, {
        body: data.message,
        icon: '/static/images/logo.png'
    });
});
