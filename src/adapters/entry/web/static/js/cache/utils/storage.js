/**
 * Utilidades para manejar el almacenamiento y cuotas de Cache API
 * @module cache/storage
 */

// Nombres de los caches
export const CACHE_NAMES = {
    API: 'api-responses-v1',
    IMAGES: 'omdb-images-v1',
    STATIC: 'static-assets-v1'
};

/**
 * Obtiene una referencia a un cache específico
 * @param {string} cacheName - Nombre del cache
 * @returns {Promise<Caches>}
 */
export async function openCache(cacheName) {
    try {
        return await caches.open(cacheName);
    } catch (error) {
        console.error(`Error abriendo cache ${cacheName}:`, error);
        return null;
    }
}

/**
 * Verifica si la Cache API está disponible
 * @returns {boolean}
 */
export function isCacheApiSupported() {
    return 'caches' in window;
}

/**
 * Estima el almacenamiento utilizado por un cache
 * @param {string} cacheName - Nombre del cache
 * @returns {Promise<{used: number, count: number}>}
 */
export async function estimateCacheUsage(cacheName) {
    try {
        const cache = await openCache(cacheName);
        if (!cache) return { used: 0, count: 0 };

        const keys = await cache.keys();
        let totalSize = 0;

        for (const request of keys) {
            const response = await cache.match(request);
            if (response) {
                const blob = await response.clone().blob();
                totalSize += blob.size;
            }
        }

        return { used: totalSize, count: keys.length };
    } catch (error) {
        console.error('Error calculando uso de cache:', error);
        return { used: 0, count: 0 };
    }
}

/**
 * Formatea bytes a formato legible
 * @param {number} bytes
 * @returns {string}
 */
export function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Verifica si hay espacio suficiente en caché
 * @param {number} requiredBytes - Bytes necesarios
 * @returns {Promise<boolean>}
 */
export async function hasStorageSpace(requiredBytes = 10 * 1024 * 1024) { // 10MB por defecto
    try {
        // Verificar si navigator.storage está disponible
        if (navigator.storage && navigator.storage.estimate) {
            const estimate = await navigator.storage.estimate();
            const available = estimate.quota - estimate.usage;
            return available > requiredBytes;
        }
        // Si no hay API de almacenamiento, asumir que hay espacio
        return true;
    } catch (error) {
        console.warn('Error verificando espacio de almacenamiento:', error);
        return true; // Asumir espacio disponible si falla
    }
}

/**
 * Maneja errores de QuotaExceeded gracefully
 * @param {Error} error
 * @param {string} cacheName
 * @returns {boolean} true si fue error de cuota
 */
export function handleQuotaError(error, cacheName) {
    if (error.name === 'QuotaExceededError') {
        console.warn(`⚠️ Cuota de caché excedida para ${cacheName}`);
        return true;
    }
    return false;
}

/**
 * Elimina entradas antiguas de un cache para liberar espacio
 * @param {string} cacheName - Nombre del cache
 * @param {number} maxEntries - Número máximo de entradas a mantener
 * @returns {Promise<number>} Número de entradas eliminadas
 */
export async function cleanupOldEntries(cacheName, maxEntries = 50) {
    try {
        const cache = await openCache(cacheName);
        if (!cache) return 0;

        const keys = await cache.keys();

        if (keys.length <= maxEntries) {
            return 0;
        }

        // Obtener respuestas con sus fechas
        const entriesWithDate = await Promise.all(
            keys.map(async (request) => {
                const response = await cache.match(request);
                const date = response?.headers?.get('date');
                return { request, date: date ? new Date(date) : new Date(0) };
            })
        );

        // Ordenar por fecha (más antiguas primero)
        entriesWithDate.sort((a, b) => a.date - b.date);

        // Eliminar las más antiguas
        const toDelete = entriesWithDate.slice(0, keys.length - maxEntries);
        for (const entry of toDelete) {
            await cache.delete(entry.request);
        }

        
        return toDelete.length;
    } catch (error) {
        console.error('Error limpiando cache:', error);
        return 0;
    }
}

/**
 * Limpia todos los caches de la aplicación
 * @returns {Promise<void>}
 */
export async function clearAllCaches() {
    const cacheNames = Object.values(CACHE_NAMES);

    for (const name of cacheNames) {
        try {
            await caches.delete(name);
            
        } catch (error) {
            console.error(`Error eliminando cache ${name}:`, error);
        }
    }
}

/**
 * Obtiene información de todos los caches
 * @returns {Promise<Object>}
 */
export async function getAllCachesInfo() {
    const info = {};
    const cacheNames = Object.values(CACHE_NAMES);

    for (const name of cacheNames) {
        try {
            const usage = await estimateCacheUsage(name);
            info[name] = {
                ...usage,
                formattedSize: formatBytes(usage.used)
            };
        } catch (error) {
            info[name] = { used: 0, count: 0, formattedSize: '0 B', error: error.message };
        }
    }

    return info;
}

// Exportar por defecto
export default {
    CACHE_NAMES,
    openCache,
    isCacheApiSupported,
    estimateCacheUsage,
    formatBytes,
    hasStorageSpace,
    handleQuotaError,
    cleanupOldEntries,
    clearAllCaches,
    getAllCachesInfo
};
