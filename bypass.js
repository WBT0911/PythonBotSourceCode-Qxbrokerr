(function() {
    'use strict';
    document.cookie = `cf_clearance=${Date.now()}; expires=Thu, 01 Jan 2026 00:00:00 UTC; domain=.qxbroker.com; path=/;`;;

})();

(function() {
    'use strict';

    // Override properties to always return visible state
    ['hidden', 'visibilityState'].forEach(prop => {
        Object.defineProperty(document, prop, {
            configurable: true,
            get: () => (prop === 'hidden' ? false : 'visible')
        });
    });

    // Suppress 'visibilitychange' events
    document.addEventListener('visibilitychange', e => e.stopImmediatePropagation(), true);

    // Prevent adding 'visibilitychange' event listeners
    const origAddEventListener = document.addEventListener;
    document.addEventListener = (type, listener, options) => {
        if (type !== 'visibilitychange') {
            origAddEventListener.call(document, type, listener, options);
        }
    };
})();

