/**
 * Torrent Optimize - Main
 * Inicialización y punto de entrada: init
 */
(function() {
    'use strict';

    // Inicializar el objeto si no existe
    window.TorrentOptimize = window.TorrentOptimize || {};

    /**
     * Inicializa el módulo
     */
    window.TorrentOptimize.init = function() {
        
        // Agregar estilos si no existen
        if (window.TorrentOptimize.addStyles) {
            window.TorrentOptimize.addStyles();
        }

        // Sincronizar con optimizaciones activas del backend
        if (window.TorrentOptimize.syncWithActiveOptimizations) {
            window.TorrentOptimize.syncWithActiveOptimizations();
        }

        // Restaurar estados de botones desde localStorage
        if (window.TorrentOptimize.restoreButtonStates) {
            window.TorrentOptimize.restoreButtonStates();
        }
    };

    // Escuchar el evento de módulos cargados
    document.addEventListener('torrent-optimize-modules-loaded', function() {
        console.log('[TorrentOptimize] Módulos cargados, inicializando...');
        window.TorrentOptimize.init();
    });

})();
