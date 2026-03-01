// Cache para thumbnails
const thumbnailCache = new Map();

// Exportar para uso en otros módulos
window.thumbnailCache = thumbnailCache;

// Función para verificar soporte de WebP
function checkWebPSupport() {
    return new Promise(resolve => {
        const webP = new Image();
        webP.onload = webP.onerror = function () {
            resolve(webP.height === 2);
        };
        webP.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';
    });
}

window.checkWebPSupport = checkWebPSupport;

// ==========================================
// CacheManager - Sistema de caché centralizado
// ==========================================

(function () {
    'use strict';

    const CACHE_NAMES = { API: 'api-responses-v1', IMAGES: 'omdb-images-v1' };
    const TTL = { API_LIST: 5 * 60 * 1000, API_METADATA: 30 * 60 * 1000, IMAGES: 7 * 24 * 60 * 60 * 1000, THUMBNAILS: 24 * 60 * 60 * 1000, POSTERS: 7 * 24 * 60 * 60 * 1000 };

    let apiCacheMetadata = {};
    let imageCacheMetadata = {};
    let initialized = false;
    let originalFetch = window.fetch;

    function isCacheApiSupported() { return 'caches' in window; }
    async function openCache(cacheName) { try { return await caches.open(cacheName); } catch (e) { return null; } }
    function createExpirationTimestamp(ttl) { return Date.now() + ttl; }
    function isExpired(expirationTimestamp) { return Date.now() > expirationTimestamp; }
    function getTTLForUrl(url) { return (url.includes('/api/movies') || url.includes('/api/series')) ? TTL.API_LIST : TTL.API_METADATA; }
    function getImageTTL(type) { return type === 'poster' ? TTL.POSTERS : type === 'thumbnail' ? TTL.THUMBNAILS : TTL.IMAGES; }

    function isImageUrl(url) {
        const imageExtensions = /\.(jpg|jpeg|png|gif|webp|svg|ico)$/i;
        const imagePaths = ['/proxy-image', '/thumbnails/', '/posters/', '/api/serie-poster', '/api/movie-thumbnail'];
        return imageExtensions.test(url) || imagePaths.some(path => url.includes(path));
    }

    // API Cache
    async function apiCacheGet(url) {
        try {
            const cache = await openCache(CACHE_NAMES.API);
            if (!cache) return null;
            const cachedResponse = await cache.match(url);
            if (!cachedResponse) return null;
            const metadata = apiCacheMetadata[url];
            if (metadata && isExpired(metadata.expiration)) { await apiCacheDelete(url); return null; }
            return cachedResponse.clone();
        } catch (e) { return null; }
    }

    async function apiCacheSet(url, response) {
        try {
            const cache = await openCache(CACHE_NAMES.API);
            if (!cache || !response.ok) return false;
            await cache.put(url, response.clone());
            apiCacheMetadata[url] = { expiration: createExpirationTimestamp(getTTLForUrl(url)), cachedAt: Date.now() };
            saveApiMetadata();
            return true;
        } catch (e) { return false; }
    }

    async function apiCacheDelete(url) {
        try {
            const cache = await openCache(CACHE_NAMES.API);
            if (cache) await cache.delete(url);
            delete apiCacheMetadata[url];
            saveApiMetadata();
            return true;
        } catch (e) { return false; }
    }

    function saveApiMetadata() { try { sessionStorage.setItem('api-cache-metadata', JSON.stringify(apiCacheMetadata)); } catch (e) { } }
    function loadApiMetadata() { try { apiCacheMetadata = JSON.parse(sessionStorage.getItem('api-cache-metadata') || '{}'); } catch (e) { apiCacheMetadata = {}; } }

    // Image Cache
    async function imageCacheGet(url) {
        try {
            const cache = await openCache(CACHE_NAMES.IMAGES);
            if (!cache) return null;
            const metadata = imageCacheMetadata[url];
            if (metadata && isExpired(metadata.expiration)) { await imageCacheDelete(url); return null; }
            const cachedResponse = await cache.match(url);
            if (!cachedResponse) return null;
            const blob = await cachedResponse.blob();
            const objectUrl = URL.createObjectURL(blob);
            return { blob, url: objectUrl, originalUrl: url };
        } catch (e) { return null; }
    }

    async function imageCacheSet(url, response, type) {
        try {
            const cache = await openCache(CACHE_NAMES.IMAGES);
            if (!cache || !response.ok) return false;
            await cache.put(url, response.clone());
            imageCacheMetadata[url] = { expiration: createExpirationTimestamp(getImageTTL(type)), cachedAt: Date.now(), type };
            saveImageMetadata();
            return true;
        } catch (e) { return false; }
    }

    async function imageCacheDelete(url) {
        try {
            const cache = await openCache(CACHE_NAMES.IMAGES);
            if (cache) await cache.delete(url);
            delete imageCacheMetadata[url];
            saveImageMetadata();
            return true;
        } catch (e) { return false; }
    }

    function saveImageMetadata() { try { localStorage.setItem('image-cache-metadata', JSON.stringify(imageCacheMetadata)); } catch (e) { } }
    function loadImageMetadata() { try { imageCacheMetadata = JSON.parse(localStorage.getItem('image-cache-metadata') || '{}'); } catch (e) { imageCacheMetadata = {}; } }

    // Fetch Interceptor
    function setupFetchInterceptor() {
        window.fetch = async function (input, init = {}) {
            const url = typeof input === 'string' ? input : input.url;
            const method = init.method || 'GET';

            if (method !== 'GET') return originalFetch(input, init);
            if (url.includes('?refresh=true')) return originalFetch(input, init);

            const isImage = isImageUrl(url);
            const isApi = url.includes('/api/');

            try {
                if (isApi) {
                    const cachedResponse = await apiCacheGet(url);
                    if (cachedResponse) { console.log('📦 API Cache HIT:', url); return cachedResponse; }
                    console.log('🌐 API Cache MISS:', url);
                    const networkResponse = await originalFetch(input, init);
                    if (networkResponse.ok) apiCacheSet(url, networkResponse.clone());
                    return networkResponse;
                } else if (isImage) {
                    let imageType = 'default';
                    if (url.includes('/api/serie-poster')) imageType = 'poster';
                    else if (url.includes('/api/movie-thumbnail')) imageType = 'thumbnail';

                    const cached = await imageCacheGet(url);
                    if (cached) { console.log('📦 Image Cache HIT:', url); return new Response(cached.blob, { status: 200, headers: { 'Content-Type': 'image/jpeg' } }); }
                    console.log('🌐 Image Cache MISS:', url);
                    const networkResponse = await originalFetch(input, init);
                    if (networkResponse.ok) imageCacheSet(url, networkResponse.clone(), imageType);
                    return networkResponse;
                }
            } catch (error) { return originalFetch(input, init); }
            return originalFetch(input, init);
        };
    }

    // Image Loader - Verifica caché antes de cargar imágenes
    function setupImageLoader() {
        const originalImageSrc = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src');

        Object.defineProperty(HTMLImageElement.prototype, 'src', {
            get: function () { return originalImageSrc.get.call(this); },
            set: function (newValue) {
                const img = this;
                const url = newValue;

                if (url && url !== '/static/images/default.jpg' && !url.startsWith('data:')) {
                    imageCacheGet(url).then(cached => {
                        if (cached && cached.blob) {
                            console.log('📦 Imagen desde caché:', url);
                            originalImageSrc.set.call(img, cached.url);
                        } else {
                            originalImageSrc.set.call(img, url);
                        }
                    }).catch(() => { originalImageSrc.set.call(img, url); });
                } else {
                    originalImageSrc.set.call(this, newValue);
                }
            }
        });
    }

    // API pública
    async function getCachedImageUrl(url) { const cached = await imageCacheGet(url); return cached ? cached.url : url; }
    async function preloadImages(urls, type) { if (!urls || !urls.length) return; for (const url of urls.slice(0, 20)) { try { const r = await fetch(url); if (r.ok) await imageCacheSet(url, r, type); } catch (e) { } } }
    async function invalidateApiCache(url) { if (url) { await apiCacheDelete(url); } else { const c = await openCache(CACHE_NAMES.API); if (c) for (const k of await c.keys()) await c.delete(k); apiCacheMetadata = {}; saveApiMetadata(); } }
    async function clearAllCaches() { await caches.delete(CACHE_NAMES.API); await caches.delete(CACHE_NAMES.IMAGES); apiCacheMetadata = {}; imageCacheMetadata = {}; saveApiMetadata(); saveImageMetadata(); }
    async function getStats() { const apiC = await openCache(CACHE_NAMES.API); const imgC = await openCache(CACHE_NAMES.IMAGES); return { apiEntries: apiC ? (await apiC.keys()).length : 0, imageEntries: imgC ? (await imgC.keys()).length : 0 }; }

    function init() {
        if (initialized) return;
        if (!isCacheApiSupported()) { console.warn('⚠️ Cache API no soportada'); return; }
        loadApiMetadata();
        loadImageMetadata();
        setupFetchInterceptor();
        setupImageLoader();
        initialized = true;
        console.log('✅ CacheManager inicializado');
    }

    window.CacheManager = { init, getCachedImageUrl, preloadImages, invalidateApiCache, clearAllCaches, getStats };
})();
