/**
 * CacheManager - Sistema de caché centralizado para la aplicación
 * Implementa estrategia Cache-First con fallback a red
 * Versión compatible sin ES modules
 */

(function () {
    'use strict';

    // Nombres de caches
    const CACHE_NAMES = {
        API: 'api-responses-v1',
        IMAGES: 'omdb-images-v1',
        STATIC: 'static-assets-v1'
    };

    // TTLs predefinidos
    const TTL = {
        API_LIST: 5 * 60 * 1000,
        API_METADATA: 30 * 60 * 1000,
        IMAGES: 7 * 24 * 60 * 60 * 1000,
        THUMBNAILS: 24 * 60 * 60 * 1000,
        POSTERS: 7 * 24 * 60 * 60 * 1000
    };

    // Estado interno
    let apiCacheMetadata = {};
    let imageCacheMetadata = {};
    let initialized = false;

    // ==========================================
    // Utilidades de almacenamiento
    // ==========================================

    function isCacheApiSupported() {
        return 'caches' in window;
    }

    async function openCache(cacheName) {
        try {
            return await caches.open(cacheName);
        } catch (error) {
            console.error('Error abriendo cache:', error);
            return null;
        }
    }

    function createExpirationTimestamp(ttl) {
        return Date.now() + ttl;
    }

    function isExpired(expirationTimestamp) {
        return Date.now() > expirationTimestamp;
    }

    function getTTLForUrl(url) {
        if (url.includes('/api/movies') || url.includes('/api/series')) {
            return TTL.API_LIST;
        }
        return TTL.API_METADATA;
    }

    function getImageTTL(type) {
        switch (type) {
            case 'poster': return TTL.POSTERS;
            case 'thumbnail': return TTL.THUMBNAILS;
            default: return TTL.IMAGES;
        }
    }

    // ==========================================
    // API Cache
    // ==========================================

    async function apiCacheGet(url) {
        try {
            const cache = await openCache(CACHE_NAMES.API);
            if (!cache) return null;

            const cachedResponse = await cache.match(url);
            if (!cachedResponse) return null;

            const metadata = apiCacheMetadata[url];
            if (metadata && isExpired(metadata.expiration)) {
                await apiCacheDelete(url);
                return null;
            }

            return cachedResponse.clone();
        } catch (error) {
            return null;
        }
    }

    async function apiCacheSet(url, response) {
        try {
            const cache = await openCache(CACHE_NAMES.API);
            if (!cache) return false;

            if (!response.ok) return false;

            const responseClone = response.clone();
            const ttl = getTTLForUrl(url);

            await cache.put(url, responseClone);
            apiCacheMetadata[url] = {
                expiration: createExpirationTimestamp(ttl),
                cachedAt: Date.now()
            };

            saveApiMetadata();
            return true;
        } catch (error) {
            return false;
        }
    }

    async function apiCacheDelete(url) {
        try {
            const cache = await openCache(CACHE_NAMES.API);
            if (cache) await cache.delete(url);
            delete apiCacheMetadata[url];
            saveApiMetadata();
            return true;
        } catch (error) {
            return false;
        }
    }

    function saveApiMetadata() {
        try {
            sessionStorage.setItem('api-cache-metadata', JSON.stringify(apiCacheMetadata));
        } catch (e) { }
    }

    function loadApiMetadata() {
        try {
            apiCacheMetadata = JSON.parse(sessionStorage.getItem('api-cache-metadata') || '{}');
        } catch (e) {
            apiCacheMetadata = {};
        }
    }

    // ==========================================
    // Image Cache
    // ==========================================

    async function imageCacheGet(url) {
        try {
            const cache = await openCache(CACHE_NAMES.IMAGES);
            if (!cache) return null;

            const metadata = imageCacheMetadata[url];
            if (metadata && isExpired(metadata.expiration)) {
                await imageCacheDelete(url);
                return null;
            }

            const cachedResponse = await cache.match(url);
            if (!cachedResponse) return null;

            const blob = await cachedResponse.blob();
            const objectUrl = URL.createObjectURL(blob);

            return { blob, url: objectUrl, originalUrl: url };
        } catch (error) {
            return null;
        }
    }

    async function imageCacheSet(url, response, type) {
        try {
            const cache = await openCache(CACHE_NAMES.IMAGES);
            if (!cache) return false;

            if (!response.ok) return false;

            const responseClone = response.clone();
            const ttl = getImageTTL(type);

            await cache.put(url, responseClone);
            imageCacheMetadata[url] = {
                expiration: createExpirationTimestamp(ttl),
                cachedAt: Date.now(),
                type
            };

            saveImageMetadata();
            return true;
        } catch (error) {
            return false;
        }
    }

    async function imageCacheDelete(url) {
        try {
            const cache = await openCache(CACHE_NAMES.IMAGES);
            if (cache) await cache.delete(url);
            delete imageCacheMetadata[url];
            saveImageMetadata();
            return true;
        } catch (error) {
            return false;
        }
    }

    function saveImageMetadata() {
        try {
            localStorage.setItem('image-cache-metadata', JSON.stringify(imageCacheMetadata));
        } catch (e) { }
    }

    function loadImageMetadata() {
        try {
            imageCacheMetadata = JSON.parse(localStorage.getItem('image-cache-metadata') || '{}');
        } catch (e) {
            imageCacheMetadata = {};
        }
    }

    // ==========================================
    // Fetch Interceptor
    // ==========================================

    let originalFetch = window.fetch;

    function setupFetchInterceptor() {
        window.fetch = async function (input, init = {}) {
            const url = typeof input === 'string' ? input : input.url;
            const method = init.method || 'GET';

            if (method !== 'GET') {
                return originalFetch(input, init);
            }

            // URLs a omitir
            if (url.includes('?refresh=true')) {
                return originalFetch(input, init);
            }

            const isImage = isImageUrl(url);
            const isApi = url.includes('/api/');

            try {
                if (isApi) {
                    return await handleApiRequest(url, originalFetch, input, init);
                } else if (isImage) {
                    return await handleImageRequest(url, originalFetch, input, init);
                }
            } catch (error) {
                return originalFetch(input, init);
            }

            return originalFetch(input, init);
        };
    }

    function isImageUrl(url) {
        const imageExtensions = /\.(jpg|jpeg|png|gif|webp|svg|ico)$/i;
        const imagePaths = ['/proxy-image', '/thumbnails/', '/posters/'];

        return imageExtensions.test(url) ||
            imagePaths.some(path => url.includes(path));
    }

    async function handleApiRequest(url, originalFetch, input, init) {
        const cachedResponse = await apiCacheGet(url);

        if (cachedResponse) {
            console.log('📦 API Cache HIT:', url);
            return cachedResponse;
        }

        console.log('🌐 API Cache MISS:', url);
        const networkResponse = await originalFetch(input, init);

        if (networkResponse.ok) {
            apiCacheSet(url, networkResponse.clone());
        }

        return networkResponse;
    }

    async function handleImageRequest(url, originalFetch, input, init) {
        let imageType = 'default';
        if (url.includes('/api/serie-poster')) {
            imageType = 'poster';
        } else if (url.includes('/api/movie-thumbnail')) {
            imageType = 'thumbnail';
        }

        const cached = await imageCacheGet(url);

        if (cached) {
            console.log('📦 Image Cache HIT:', url);
            return new Response(cached.blob, {
                status: 200,
                headers: { 'Content-Type': 'image/jpeg' }
            });
        }

        console.log('🌐 Image Cache MISS:', url);
        const networkResponse = await originalFetch(input, init);

        if (networkResponse.ok) {
            imageCacheSet(url, networkResponse.clone(), imageType);
        }

        return networkResponse;
    }

    // ==========================================
    // CacheManager API pública
    // ==========================================

    async function getCachedImageUrl(url) {
        const cached = await imageCacheGet(url);
        return cached ? cached.url : url;
    }

    async function preloadImages(urls, type) {
        if (!urls || urls.length === 0) return;

        const urlsToPreload = urls.slice(0, 20);

        for (const url of urlsToPreload) {
            try {
                if (!imageCacheMetadata[url] || isExpired(imageCacheMetadata[url].expiration)) {
                    const response = await fetch(url);
                    if (response.ok) {
                        await imageCacheSet(url, response, type);
                    }
                }
            } catch (e) { }
        }

        console.log(`🖼️ Precargadas ${urlsToPreload.length} imágenes`);
    }

    async function invalidateApiCache(url) {
        if (url) {
            await apiCacheDelete(url);
        } else {
            const cache = await openCache(CACHE_NAMES.API);
            if (cache) {
                const keys = await cache.keys();
                for (const request of keys) {
                    await cache.delete(request);
                }
            }
            apiCacheMetadata = {};
            saveApiMetadata();
        }
        console.log('🗑️ Caché API invalidado');
    }

    async function invalidateImageCache(url) {
        if (url) {
            await imageCacheDelete(url);
        } else {
            const cache = await openCache(CACHE_NAMES.IMAGES);
            if (cache) {
                const keys = await cache.keys();
                for (const request of keys) {
                    await cache.delete(request);
                }
            }
            imageCacheMetadata = {};
            saveImageMetadata();
        }
        console.log('🗑️ Caché de imágenes invalidado');
    }

    async function clearAllCaches() {
        await caches.delete(CACHE_NAMES.API);
        await caches.delete(CACHE_NAMES.IMAGES);
        apiCacheMetadata = {};
        imageCacheMetadata = {};
        saveApiMetadata();
        saveImageMetadata();
        console.log('🗑️ Todos los caches limpiados');
    }

    async function getStats() {
        const apiCache = await openCache(CACHE_NAMES.API);
        const imageCache = await openCache(CACHE_NAMES.IMAGES);

        const apiKeys = apiCache ? await apiCache.keys() : [];
        const imageKeys = imageCache ? await imageCache.keys() : [];

        return {
            apiEntries: apiKeys.length,
            imageEntries: imageKeys.length,
            apiMetadata: Object.keys(apiCacheMetadata).length,
            imageMetadata: Object.keys(imageCacheMetadata).length
        };
    }

    function init() {
        if (initialized) return;
        if (!isCacheApiSupported()) {
            console.warn('⚠️ Cache API no soportada');
            return;
        }

        loadApiMetadata();
        loadImageMetadata();
        setupFetchInterceptor();
        initialized = true;

        console.log('✅ CacheManager inicializado');
    }

    // Exponer API globalmente
    window.CacheManager = {
        init,
        getCachedImageUrl,
        preloadImages,
        invalidateApiCache,
        invalidateImageCache,
        clearAllCaches,
        getStats
    };

})();
