// taken from https://github.com/silviolleite/django-pwa/blob/master/pwa/templates/serviceworker.js
// MIT License (MIT)
//
// Copyright (c) 2014 Scott Vitale, Silvio Luis and Contributors
//
// Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

const staticCacheName = "ephios-pwa-v" + new Date().getTime();
const staticFilesToCacheOnInstall = [
    '/offline/',
    '/events/',
    '/',
    "/manifest.json",
    "/static/ephios/img/ephios-192x.png",
    "/static/ephios/img/ephios-512x.png",
    "/static/ephios/img/ephios-1024x.png",
    "/static/ephios/img/ephios-symbol-red.svg",
    "/static/ephios/img/ephios-text-black.png",
];

// Cache on install
self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(staticCacheName).then(cache => {
            return cache.addAll(staticFilesToCacheOnInstall);
        })
    );
});

// Clear cache on activate
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
                    if (event.request.method === "GET") {
                        // This will inadvertedly cache pages with messages in them
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
    )
    ;
})
;