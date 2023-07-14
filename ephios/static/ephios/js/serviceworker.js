const staticCacheName = "ephios-pwa-v" + new Date().getTime();
const staticFilesToCacheOnInstall = [
    '/offline/',
    "/manifest.json",
    "/static/ephios/img/ephios-192x.png",
    "/static/ephios/img/ephios-512x.png",
    "/static/ephios/img/ephios-1024x.png",
    "/static/ephios/img/ephios-symbol-red.svg",
    "/static/ephios/img/ephios-text-black.png",
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(staticCacheName).then(cache => {
            return cache.addAll(staticFilesToCacheOnInstall);
        })
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(cacheName => (cacheName.startsWith("ephios-pwa-")))
                    .filter(cacheName => (cacheName !== staticCacheName))
                    .map(cacheName => caches.delete(cacheName))
            );
        })
    );
});

self.addEventListener("fetch", event => {
    event.respondWith(
        caches.open(staticCacheName).then(function (cache) {
            const isStatic = new URL(event.request.url).pathname.startsWith("/static/");
            if (isStatic) {
                // Return static files from the cache by default,
                // falling back to network and caching it then.
                return cache.match(event.request).then(function (response) {
                    return response || fetch(event.request).then(function (response) {
                        cache.put(event.request, response.clone());
                        return response;
                    });
                });
            } else {
                // Serve dynamic content from network, falling back to cache when offline.
                // Cache network responses for the offline case.
                return fetch(event.request).then(function (response) {
                    if (event.request.method === "GET" && response.status === 200) {
                        // This will inadvertently cache pages with messages in them
                        cache.put(event.request, response.clone());
                    }
                    return response;
                }).catch(() => {
                    return cache.match(event.request).then(function (response) {
                        if (response) {
                            return response.body.getReader().read().then((result) => {
                                let body = new TextDecoder().decode(result.value);
                                // this is somewhat hacky, but it works to communicate to the frontend that we are offline
                                body = body.replace("data-pwa-network=\"online\"", "data-pwa-network=\"offline\"");
                                return new Response(
                                    new TextEncoder().encode(body),
                                    {
                                        headers: response.headers,
                                        status: response.status,
                                        statusText: response.statusText
                                    }
                                );
                            });
                        }
                        return cache.match('/offline/');
                    });
                });
            }
        })
    );
});