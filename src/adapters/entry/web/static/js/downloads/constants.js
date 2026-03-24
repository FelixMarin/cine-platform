/**
 * Constantes del módulo de descargas
 * CONFIGuración y patrones de detección de idioma español
 */

(function() {
    'use strict';

    // ==========================================================================
    // CONFIGURACIÓN
    // ==========================================================================

    window.CONFIG = {
        pollInterval: 3000,          // Intervalo de polling en ms
        maxHistoryItems: 50,         // Máximo elementos en historial
        endpoints: {
            search: '/api/search-movie',
            downloadTorrent: '/api/download-torrent',
            downloadUrl: '/api/download-url',
            downloadsActive: '/api/downloads/active',
            downloadStatus: (id) => `/api/downloads/${id}/status`,
            downloadCancel: (id) => `/api/downloads/${id}/cancel`,
            downloadStop: (id) => `/api/download-stop/${id}`,
            downloadStart: (id) => `/api/download-start/${id}`,
            downloadRemove: (id) => `/api/download-remove/${id}`,
            optimizeStart: '/api/optimizer/optimize',
            optimizeStatus: '/api/optimizer/status',
            optimizeCancel: '/api/optimizer/cancel',
            optimizeProfiles: '/api/optimizer/profiles',
            torrentOptimizeActive: '/api/optimize-torrent/active',
            torrentOptimizeStatus: (id) => `/api/optimize-torrent/status/${id}`,
            torrentOptimizeStart: '/api/optimize-torrent',
            optimizationHistory: '/api/optimization-history/',
            optimizationHistoryLatest: '/api/optimization-history/latest'
        }
    };

    // ==========================================================================
    // PATRONES DE IDIOMA ESPAÑOL
    // ==========================================================================

    window.SPANISH_PATTERNS = [
        /\[esp\]/i,
        /\[español\]/i,
        /\[spanish\]/i,
        /\[castellano\]/i,
        /\bespañol\b/i,
        /\bspanish\b/i,
        /\bcastellano\b/i,
        /\bsubtitulado\b/i,
        /\bvo\b/i,
        /\bversión original\b/i,
        /\bsp\./i,
        /\besp\./i,
        /\bes(-)?es\b/i,
        /\bes(-)?la\b/i,
        /\baudio español\b/i,
        /\baudio spanish\b/i,
        /\bdoblado\b/i,
        /\bdubbed\b/i,
        /\bdub\b/i
    ];

})();
