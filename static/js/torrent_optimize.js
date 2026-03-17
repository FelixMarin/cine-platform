/**
 * TORRENT_OPTIMIZE.JS - Punto de entrada para la optimización de torrents
 * Carga los módulos dinámicamente
 * 
 * Este módulo proporciona funcionalidad para:
 * - Iniciar optimización de torrents descargados
 * - Monitorear progreso de optimización
 * - Listar optimizaciones activas
 * - Verificar disponibilidad de GPU
 */

(function() {
    'use strict';

    // Inicializar el objeto TorrentOptimize
    window.TorrentOptimize = window.TorrentOptimize || {};

    // Lista de módulos a cargar en orden
    var modules = [
        'static/js/torrent_optimize/constants.js',
        'static/js/torrent_optimize/utils.js',
        'static/js/torrent_optimize/storage.js',
        'static/js/torrent_optimize/api.js',
        'static/js/torrent_optimize/buttons.js',
        'static/js/torrent_optimize/sync.js',
        'static/js/torrent_optimize/progress.js',
        'static/js/torrent_optimize/polling.js',
        'static/js/torrent_optimize/styles.js',
        'static/js/torrent_optimize/modal.js',
        'static/js/torrent_optimize/main.js'
    ];

    var loadedCount = 0;
    var failedModules = [];

    function loadModule(url) {
        return new Promise(function(resolve, reject) {
            var script = document.createElement('script');
            script.src = url;
            script.onload = function() {
                console.log('[TorrentOptimize] Módulo cargado: ' + url);
                resolve();
            };
            script.onerror = function() {
                console.error('[TorrentOptimize] Error cargando módulo: ' + url);
                failedModules.push(url);
                resolve(); // Resolvemos para continuar con otros módulos
            };
            document.head.appendChild(script);
        });
    }

    async function loadAllModules() {
        console.log('[TorrentOptimize] Iniciando carga de módulos...');
        
        for (var i = 0; i < modules.length; i++) {
            await loadModule(modules[i]);
        }

        if (failedModules.length > 0) {
            console.warn('[TorrentOptimize] Algunos módulos no se cargaron:', failedModules);
        }

        console.log('[TorrentOptimize] Todos los módulos procesados, disparando evento...');
        
        // Disparar evento cuando terminen de cargar
        var event = new CustomEvent('torrent-optimize-modules-loaded');
        document.dispatchEvent(event);
    }

    // Iniciar carga cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadAllModules);
    } else {
        loadAllModules();
    }

})();
