/**
 * Torrent Optimize - Constants
 * Constantes: POLL_INTERVAL, BUTTON_STATES, STORAGE_KEY, STORAGE_TIMEOUT
 */
(function() {
    'use strict';

    // Inicializar el objeto si no existe
    window.TorrentOptimize = window.TorrentOptimize || {};

    // Intervalo de polling (2 segundos)
    window.TorrentOptimize.POLL_INTERVAL = 2000;

    // Estados del botón GPU Optimize
    window.TorrentOptimize.BUTTON_STATES = {
        IDLE: 'idle',           // No optimizado o error - habilitado verde
        OPTIMIZING: 'optimizing', // Optimizando - deshabilitado amarillo
        OPTIMIZED: 'optimized',   // Optimizado con éxito - deshabilitado gris
        ERROR: 'error'            // Error - habilitado verde para reintentar
    };

    // Clave para localStorage
    window.TorrentOptimize.STORAGE_KEY = 'cine-platform-optimize-processes';
    
    // Timeout para localStorage (5 minutos)
    window.TorrentOptimize.STORAGE_TIMEOUT = 5 * 60 * 1000;

})();
