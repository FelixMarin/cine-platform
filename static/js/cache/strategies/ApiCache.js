/**
 * Estrategia de caché para endpoints JSON de la API
 * @module cache/ApiCache
 */

import { CACHE_NAMES, openCache, hasStorageSpace, handleQuotaError } from '../utils/storage.js';
import { createExpirationTimestamp, isExpired, getTTLForUrl } from '../utils/expiration.js';

/**
 * Clase para manejar el caché de respuestas JSON de la API
 */
class ApiCache {
    constructor() {
        this.cacheName = CACHE_NAMES.API;
        this.metadataCacheName = 'api-metadata-v1';
        this.defaultTTL = 5 * 60 * 1000; // 5 minutos por defecto
        this.initialized = false;
    }

    /**
     * Inicializa el cache creando las tiendas de metadatos necesarias
     */
    async init() {
        if (this.initialized) return;

        try {
            // Asegurar que el cache existe
            await openCache(this.cacheName);

            // Inicializar metadata cache en sessionStorage para mayor velocidad
            if (!sessionStorage.getItem(this.metadataCacheName)) {
                sessionStorage.setItem(this.metadataCacheName, JSON.stringify({}));
            }

            this.initialized = true;
            console.log('✅ ApiCache inicializado');
        } catch (error) {
            console.error('Error inicializando ApiCache:', error);
        }
    }

    /**
     * Obtiene los metadatos de una entrada de caché
     * @param {string} url - URL de la petición
     * @returns {Object|null}
     */
    getMetadata(url) {
        try {
            const metadata = JSON.parse(sessionStorage.getItem(this.metadataCacheName) || '{}');
            return metadata[url] || null;
        } catch (e) {
            return null;
        }
    }

    /**
     * Guarda metadatos de una entrada de caché
     * @param {string} url - URL de la petición
     * @param {Object} data - Metadatos a guardar
     */
    setMetadata(url, data) {
        try {
            const metadata = JSON.parse(sessionStorage.getItem(this.metadataCacheName) || '{}');
            metadata[url] = data;
            sessionStorage.setItem(this.metadataCacheName, JSON.stringify(metadata));
        } catch (e) {
            console.warn('Error guardando metadatos de caché:', e);
        }
    }

    /**
     * Elimina metadatos de una entrada de caché
     * @param {string} url - URL de la petición
     */
    deleteMetadata(url) {
        try {
            const metadata = JSON.parse(sessionStorage.getItem(this.metadataCacheName) || '{}');
            delete metadata[url];
            sessionStorage.setItem(this.metadataCacheName, JSON.stringify(metadata));
        } catch (e) {
            // Ignorar errores
        }
    }

    /**
     * Obtiene una respuesta del caché
     * @param {string} url - URL de la petición
     * @returns {Promise<Response|null>}
     */
    async get(url) {
        try {
            const cache = await openCache(this.cacheName);
            if (!cache) return null;

            // Verificar si existe en cache
            const cachedResponse = await cache.match(url);
            if (!cachedResponse) {
                return null;
            }

            // Verificar expiración usando metadatos
            const metadata = this.getMetadata(url);
            if (metadata && isExpired(metadata.expiration)) {
                // Expirado - eliminar
                await this.delete(url);
                return null;
            }

            // Clonar para no consumir el body
            return cachedResponse.clone();
        } catch (error) {
            console.warn('Error leyendo de ApiCache:', error);
            return null;
        }
    }

    /**
     * Guarda una respuesta en el caché
     * @param {string} url - URL de la petición
     * @param {Response} response - Respuesta a cachear
     * @param {number} ttl - Tiempo de vida opcional
     * @returns {Promise<boolean>}
     */
    async set(url, response, ttl = null) {
        try {
            // Verificar espacio disponible
            if (!await hasStorageSpace(1024 * 1024)) { // 1MB mínimo
                console.warn('⚠️ Espacio insuficiente para cachear API response');
                return false;
            }

            const cache = await openCache(this.cacheName);
            if (!cache) return false;

            // Clonar la respuesta porque solo puede leerse una vez
            const responseClone = response.clone();

            // Solo cachear respuestas exitosas
            if (!responseClone.ok) {
                return false;
            }

            // Calcular TTL
            const actualTTL = ttl || getTTLForUrl(url, 'api');
            const expiration = createExpirationTimestamp(actualTTL);

            // Guardar en cache
            await cache.put(url, responseClone);

            // Guardar metadatos
            this.setMetadata(url, {
                expiration,
                cachedAt: Date.now(),
                ttl: actualTTL,
                status: response.status
            });

            return true;
        } catch (error) {
            if (handleQuotaError(error, this.cacheName)) {
                // Limpiar entradas antiguas y reintentar
                const { cleanupOldEntries } = await import('../utils/storage.js');
                await cleanupOldEntries(this.cacheName, 30);
                return this.set(url, response, ttl);
            }
            console.warn('Error guardando en ApiCache:', error);
            return false;
        }
    }

    /**
     * Elimina una entrada del caché
     * @param {string} url - URL de la petición
     * @returns {Promise<boolean>}
     */
    async delete(url) {
        try {
            const cache = await openCache(this.cacheName);
            if (!cache) return false;

            const deleted = await cache.delete(url);
            this.deleteMetadata(url);
            return deleted;
        } catch (error) {
            console.warn('Error eliminando de ApiCache:', error);
            return false;
        }
    }

    /**
     * Verifica si una URL está cacheda y no ha expirado
     * @param {string} url - URL a verificar
     * @returns {Promise<boolean>}
     */
    async hasValid(url) {
        const cached = await this.get(url);
        if (cached) {
            return true;
        }
        return false;
    }

    /**
     * Invalidar todo el caché de API
     */
    async clear() {
        try {
            const cache = await openCache(this.cacheName);
            if (cache) {
                const keys = await cache.keys();
                for (const request of keys) {
                    await cache.delete(request);
                }
            }
            sessionStorage.setItem(this.metadataCacheName, JSON.stringify({}));
            console.log('🗑️ ApiCache limpiado');
        } catch (error) {
            console.error('Error limpiando ApiCache:', error);
        }
    }

    /**
     * Obtiene estadísticas del caché
     * @returns {Promise<Object>}
     */
    async getStats() {
        try {
            const cache = await openCache(this.cacheName);
            if (!cache) return { entries: 0, hits: 0, misses: 0 };

            const keys = await cache.keys();
            const metadata = JSON.parse(sessionStorage.getItem(this.metadataCacheName) || '{}');

            let validEntries = 0;
            let expiredEntries = 0;

            for (const request of keys) {
                const url = request.url;
                const meta = metadata[url];
                if (meta && !isExpired(meta.expiration)) {
                    validEntries++;
                } else {
                    expiredEntries++;
                }
            }

            return {
                totalEntries: keys.length,
                validEntries,
                expiredEntries,
                metadataCount: Object.keys(metadata).length
            };
        } catch (error) {
            console.error('Error obteniendo estadísticas de ApiCache:', error);
            return { entries: 0, error: error.message };
        }
    }
}

// Instancia singleton
const apiCache = new ApiCache();

export default apiCache;
export { ApiCache };
