/**
 * Utilidades para manejar la expiración de caché basada en timestamps
 * @module cache/expiration
 */

/**
 * TTLs predefinidos para diferentes tipos de recursos
 */
export const TTL = {
    // Endpoints JSON - 5 minutos para listados, 30 para metadatos
    API_LIST: 5 * 60 * 1000,        // 5 minutos
    API_METADATA: 30 * 60 * 1000,    // 30 minutos

    // Imágenes - 7 días (las imágenes cambian muy raramente)
    IMAGES: 7 * 24 * 60 * 60 * 1000, // 7 días

    // Assets estáticos - 24 horas
    STATIC: 24 * 60 * 60 * 1000,     // 24 horasnails de

    // Thumb películas - 24 horas
    THUMBNAILS: 24 * 60 * 60 * 1000, // 24 horas

    // Pósters de series - 7 días
    POSTERS: 7 * 24 * 60 * 60 * 1000 // 7 días
};

/**
 * Crea un timestamp de expiración basado en el TTL proporcionado
 * @param {number} ttl - Tiempo de vida en milisegundos
 * @returns {number} Timestamp de expiración
 */
export function createExpirationTimestamp(ttl) {
    return Date.now() + ttl;
}

/**
 * Verifica si un timestamp de expiración ha pasado
 * @param {number} expirationTimestamp - Timestamp de expiración
 * @returns {boolean} true si ha expirado
 */
export function isExpired(expirationTimestamp) {
    return Date.now() > expirationTimestamp;
}

/**
 * Calcula el tiempo restante hasta la expiración
 * @param {number} expirationTimestamp - Timestamp de expiración
 * @returns {number} Milisegundos restantes (negativo si ya expiró)
 */
export function getTimeRemaining(expirationTimestamp) {
    return expirationTimestamp - Date.now();
}

/**
 * Obtiene el TTL apropiado según el tipo de recurso
 * @param {string} url - URL del recurso
 * @param {string} type - Tipo de recurso ('api' | 'image' | 'static')
 * @returns {number} TTL en milisegundos
 */
export function getTTLForUrl(url, type = 'api') {
    // Determinar tipo automáticamente si no se especifica
    if (!type) {
        if (url.includes('/api/')) {
            type = 'api';
        } else if (url.match(/\.(jpg|jpeg|png|gif|webp|svg|ico)$/i)) {
            type = 'image';
        } else {
            type = 'static';
        }
    }

    switch (type) {
        case 'image':
            return TTL.IMAGES;
        case 'static':
            return TTL.STATIC;
        case 'api':
        default:
            // Diferenciar entre endpoints
            if (url.includes('/api/movies') || url.includes('/api/series')) {
                return TTL.API_LIST;
            }
            return TTL.API_METADATA;
    }
}

/**
 * Convierte milisegundos a formato legible
 * @param {number} ms - Milisegundos
 * @returns {string} Formato legible
 */
export function formatDuration(ms) {
    if (ms < 0) return 'expirado';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    if (ms < 3600000) return `${(ms / 60000).toFixed(1)}min`;
    return `${(ms / 3600000).toFixed(1)}h`;
}

// Exportar por defecto
export default {
    TTL,
    createExpirationTimestamp,
    isExpired,
    getTimeRemaining,
    getTTLForUrl,
    formatDuration
};
