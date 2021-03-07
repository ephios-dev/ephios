// Initialize the service worker
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/serviceworker.js', {
        scope: '/'
    }).then(function (registration) {
        // Registration was successful
        console.log('django-pwa: ServiceWorker registration successful with scope: ', registration.scope);
    }, function (err) {
        // registration failed :(
        console.log('django-pwa: ServiceWorker registration failed: ', err);
    });
}