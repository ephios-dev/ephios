const CACHE_NAME = "{{ cache_name }}";

const filesToCacheOnInstall = [
    '{{ offline_url }}',
    // We would also need to cache the css for the offline page,
    // but its name is not known due to django-compressors
    // dynamic file names, though the files will be cached on
    // subsequent visits to pages that use the same css.
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll(filesToCacheOnInstall).then(() => {
                return this.skipWaiting();
            });
        })
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(cacheName => (
                        cacheName.startsWith("ephios-pwa-") || cacheName.startsWith("django-pwa-") // old cache names
                    ))
                    .filter(cacheName => (cacheName !== CACHE_NAME))
                    .map(cacheName => caches.delete(cacheName))
            );
        })
    );
});

self.addEventListener("message", (event) => {
    if (event.data === "logout") {
        event.waitUntil(
            caches.keys().then(cacheNames => {
                console.log("Clearing cache after logout");
                return Promise.all(cacheNames.map(cacheName => caches.delete(cacheName)));
            })
        );
    }
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

async function fetchAndCacheOrCatch(event, catchCallback) {
    try {
        let response = await fetch(event.request);
        if (response.ok === undefined) {
            // fetch() on firefox does not throw an error when offline,
            // but returns an Exception object without ok property
            throw new Error("Response is not ok");
        }
        if (event.request.method === "GET" && response.ok) {
            // This will inadvertently cache pages with messages in them
            let cache = await caches.open(CACHE_NAME);
            await cache.put(event.request, response.clone());
        }
        return response;
    } catch (err) {
        return catchCallback(err);
    }
}

async function cacheThenNetwork(event) {
    let cache_response = await caches.match(event.request);
    if (cache_response) {
        return cache_response;
    }
    return fetchAndCacheOrCatch(event, async (err) => {
        throw err; // already checked the cache, so we can only fail
    })
}

async function networkThenCacheOrOffline(event) {
    return fetchAndCacheOrCatch(event, async (err) => {
        let response = await caches.match(event.request)
        if (response) {
            if (event.request.mode === "navigate") {
                // mark the response document as offline, so the frontend can display a message
                response = await markResponseAsOffline(response);
            }
            return response;
        }
        return caches.match('{{ offline_url }}', {ignoreVary: true});
    })
}

self.addEventListener("fetch", event => {
    const isStatic = new URL(event.request.url).pathname.startsWith("{{ static_url }}");
    const enableCache = "{{ enable_cache }}" === "True";
    if (enableCache && isStatic) {
        event.respondWith(cacheThenNetwork(event));
    } else {
        event.respondWith(networkThenCacheOrOffline(event));
    }
});