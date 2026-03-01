/**
 * Estrategia de caché para imágenes (pósters, thumbnails)
 * @module cache/ImageCache
 */

import { CACHE_NAMES, openCache, hasStorageSpace, handleQuotaError } from '../utils/storage.js';
import { createExpirationTimestamp, isExpired, getTTLForUrl, TTL } from '../utils/expiration.js';

/**
 * Clase para manejar el caché de imágenes
 * Utiliza Cache API para almacenar blobs de imágenes
 */
class ImageCache {
    constructor() {
        this.cacheName = CACHE_NAMES.IMAGES;
        this.metadataCacheName = 'image-metadata-v1';
        this.initialized = false;

        // Métricas
        this.stats = {
            hits: 0,
            misses: 0,
            errors: 0
        };
    }

    /**
     * Inicializa el cache
     */
    async init() {
        if (this.initialized) return;

        try {
            await openCache(this.cacheName);

            // Usar localStorage para metadatos de imágenes (persisten más)
            if (!localStorage.getItem(this.metadataCacheName)) {
                localStorage.setItem(this.metadataCacheName, JSON.stringify({}));
            }

            this.initialized = true;
            console.log('✅ ImageCache inicializado');
        } catch (error) {
            console.error('Error inicializando ImageCache:', error);
        }
    }

    /**
     * Obtiene los metadatos de una imagen
     * @param {string} url - URL de la imagen
     * @returns {Object|null}
     */
    getMetadata(url) {
        try {
            const metadata = JSON.parse(localStorage.getItem(this.metadataCacheName) || '{}');
            return metadata[url] || null;
        } catch (e) {
            return null;
        }
    }

    /**
     * Guarda metadatos de una imagen
     * @param {string} url - URL de la imagen
     * @param {Object} data - Metadatos
     */
    setMetadata(url, data) {
        try {
            const metadata = JSON.parse(localStorage.getItem(this.metadataCacheName) || '{}');
            metadata[url] = data;
            // Limitar metadatos para evitar localStorage lleno
            const keys = Object.keys(metadata);
            if (keys.length > 200) {
                // Eliminar las más antiguas
                const sorted = keys.sort((a, b) =>
                    (metadata[b].cachedAt || 0) - (metadata[a].cachedAt || 0)
                );
                for (let i = 100; i < sorted.length; i++) {
                    delete metadata[sorted[i]];
                }
            }
            localStorage.setItem(this.metadataCacheName, JSON.stringify(metadata));
        } catch (e) {
            console.warn('Error guardando metadatos de imagen:', e);
        }
    }

    /**
     * Obtiene una imagen del caché
     * @param {string} url - URL de la imagen
     * @returns {Promise<{blob: Blob, url: string}|null>}
     */
    async get(url) {
        try {
            const cache = await openCache(this.cacheName);
            if (!cache) return null;

            // Verificar metadatos primero
            const metadata = this.getMetadata(url);
            if (metadata && isExpired(metadata.expiration)) {
                await this.delete(url);
                return null;
            }

            const cachedResponse = await cache.match(url);
            if (!cachedResponse) {
                this.stats.misses++;
                return null;
            }

            // Verificar que es una respuesta válida
            if (!cachedResponse.ok) {
                this.stats.misses++;
                return null;
            }

            const blob = await cachedResponse.blob();
            this.stats.hits++;

            // Crear URL de objeto para la imagen
            const objectUrl = URL.createObjectURL(blob);

            return {
                blob,
                url: objectUrl,
                originalUrl: url,
                cached: true
            };
        } catch (error) {
            this.stats.errors++;
            console.warn('Error leyendo de ImageCache:', error);
            return null;
        }
    }

    /**
     * Guarda una imagen en el caché
     * @param {string} url - URL de la imagen
     * @param {Response} response - Respuesta de red
     * @param {string} type - Tipo de imagen ('poster' | 'thumbnail' | 'default')
     * @returns {Promise<boolean>}
     */
    async set(url, response, type = 'default') {
        try {
            // Verificar espacio
            if (!await hasStorageSpace(2 * 1024 * 1024)) { // 2MB mínimo
                console.warn('⚠️ Espacio insuficiente para cachear imagen');
                return false;
            }

            const cache = await openCache(this.cacheName);
            if (!cache) return false;

            // Clonar respuesta
            const responseClone = response.clone();

            // Solo cachear respuestas exitosas
            if (!responseClone.ok) {
                return false;
            }

            // Determinar TTL según tipo
            let ttl;
            switch (type) {
                case 'poster':
                    ttl = TTL.POSTERS;
                    break;
                case 'thumbnail':
                    ttl = TTL.THUMBNAILS;
                    break;
                default:
                    ttl = TTL.IMAGES;
            }

            const expiration = createExpirationTimestamp(ttl);

            // Guardar en cache
            await cache.put(url, responseClone);

            // Guardar metadatos
            this.setMetadata(url, {
                expiration,
                cachedAt: Date.now(),
                ttl,
                type,
                size: response.headers.get('content-length') || 0
            });

            return true;
        } catch (error) {
            if (handleQuotaError(error, this.cacheName)) {
                // Limpiar y reintentar
                const { cleanupOldEntries } = await import('../utils/storage.js');
                await cleanupOldEntries(this.cacheName, 20);
                return this.set(url, response, type);
            }
            console.warn('Error guardando en ImageCache:', error);
            return false;
        }
    }

    /**
     * Elimina una imagen del caché
     * @param {string} url - URL de la imagen
     * @returns {Promise<boolean>}
     */
    async delete(url) {
        try {
            const cache = await openCache(this.cacheName);
            if (!cache) return false;

            // Liberar object URL si existe
            const metadata = this.getMetadata(url);
            if (metadata && metadata.objectUrl) {
                URL.revokeObjectURL(metadata.objectUrl);
            }

            const deleted = await cache.delete(url);

            // Eliminar metadatos
            try {
                const allMetadata = JSON.parse(localStorage.getItem(this.metadataCacheName) || '{}');
                delete allMetadata[url];
                localStorage.setItem(this.metadataCacheName, JSON.stringify(allMetadata));
            } catch (e) {
                // Ignorar
            }

            return deleted;
        } catch (error) {
            console.warn('Error eliminando de ImageCache:', error);
            return false;
        }
    }

    /**
     * Verifica si una imagen está cacheada y no ha expirado
     * @param {string} url - URL a verificar
     * @returns {Promise<boolean>}
     */
    async hasValid(url) {
        const cached = await this.get(url);
        return cached !== null;
    }

    /**
     * Precarga una imagen en segundo plano
     * @param {string} url - URL de la imagen
     * @param {string} type - Tipo de imagen
     * @returns {Promise<void>}
     */
    async preload(url, type = 'default') {
        try {
            // Ya está cacheado
            if (await this.hasValid(url)) {
                return;
            }

            const response = await fetch(url, {
                mode: 'cors',
                credentials: 'same-origin'
            });

            if (response.ok) {
                await this.set(url, response, type);
            }
        } catch (error) {
            // Silencioso - es solo precarga
        }
    }

    /**
     * Precarga múltiples imágenes
     * @param {Array<{url: string, type?: string}>} images - Array de imágenes
     * @param {number} limit - Límite de descargas simultáneas
     */
    async preloadMultiple(images, limit = 5) {
        const queue = [...images];
        const active = [];

        const processQueue = async () => {
            while (queue.length > 0 && active.length < limit) {
                const item = queue.shift();
                const promise = this.preload(item.url, item.type || 'default')
                    .finally(() => {
                        const index = active.indexOf(promise);
                        if (index > -1) active.splice(index, 1);
                    });
                active.push(promise);
            }

            if (active.length > 0) {
                await Promise.all(active);
                if (queue.length > 0) {
                    processQueue();
                }
            }
        };

        await processQueue();
    }

    /**
     * Limpia el caché de imágenes
     */
    async clear() {
        try {
            const cache = await openCache(this.cacheName);
            if (cache) {
                // Revocar todas las URLs de objeto primero
                const metadata = JSON.parse(localStorage.getItem(this.metadataCacheName) || '{}');
                for (const url in metadata) {
                    if (metadata[url].objectUrl) {
                        URL.revokeObjectURL(metadata[url].objectUrl);
                    }
                }

                const keys = await cache.keys();
                for (const request of keys) {
                    await cache.delete(request);
                }
            }
            localStorage.setItem(this.metadataCacheName, JSON.stringify({}));
            console.log('🗑️ ImageCache limpiado');
        } catch (error) {
            console.error('Error limpiando ImageCache:', error);
        }
    }

    /**
     * Obtiene estadísticas del caché
     * @returns {Promise<Object>}
     */
    async getStats() {
        try {
            const cache = await openCache(this.cacheName);
            if (!cache) return { ...this.stats, entries: 0 };

            const keys = await cache.keys();
            const metadata = JSON.parse(localStorage.getItem(this.metadataCacheName) || '{}');

            let validEntries = 0;
            let totalSize = 0;

            for (const request of keys) {
                const url = request.url;
                const meta = metadata[url];
                if (meta && !isExpired(meta.expiration)) {
                    validEntries++;
                    totalSize += parseInt(meta.size || 0);
                }
            }

            return {
                ...this.stats,
                entries: keys.length,
                validEntries,
                totalSize
            };
        } catch (error) {
            return { ...this.stats, error: error.message };
        }
    }
}

// Instancia singleton
const imageCache = new ImageCache();

export default imageCache;
export { ImageCache };
