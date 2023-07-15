const staticCacheName = "ephios-pwa-v1";
const staticFilesToCacheOnInstall = [
    '/offline/',
    "/static/ephios/img/ephios-192x.png",
    "/static/ephios/img/ephios-512x.png",
    "/static/ephios/img/ephios-1024x.png",
    "/static/ephios/img/ephios-symbol-red.svg",
    "/static/ephios/img/ephios-text-black.png",
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(staticCacheName).then(cache => {
            return cache.addAll(staticFilesToCacheOnInstall).then(() => {
                this.skipWaiting();
            });
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

async function markResponseAsOffline(response) {
    let content = await response.body.getReader().read().then(r => r.value);
    let body = new TextDecoder().decode(content);
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
}

async function cacheThenNetwork(event) {
    // Return static files from the cache by default,
    // falling back to network and caching it then.
    let cache_response = await caches.match(event.request);
    if (cache_response) {
        return cache_response;
    }
    let response = await fetch(event.request);
    let cache = await caches.open(staticCacheName);
    await cache.put(event.request, response.clone());
    return response;
}

async function networkThenCacheOrOffline(event) {
    // Serve dynamic content from network, falling back to cache when offline.
    // Cache network responses for the offline case.
    try {
        let response = await fetch(event.request);
        if(!response.ok ) {
            // fetch() on firefox does not throw an error when offline, but returns an Exception object
            throw new Error("Response is not ok");
        }
        if (event.request.method === "GET" && response.status === 200) {
            // This will inadvertently cache pages with messages in them
            let cache = await caches.open(staticCacheName);
            await cache.put(event.request, response.clone());
        }
        return response;
    } catch (err) {
        let response = await caches.match(event.request)
        if (response) {
            return await markResponseAsOffline(response);
        }
        return caches.match('/offline/', {ignoreVary: true});
    }
}

self.addEventListener("fetch", event => {
    const isStatic = new URL(event.request.url).pathname.startsWith("/static/");
    if (isStatic) {
        event.respondWith(cacheThenNetwork(event));
    } else {
        event.respondWith(networkThenCacheOrOffline(event));
    }
});