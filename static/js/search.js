/**
 * SEARCH.JS - Punto de entrada para la página de búsqueda
 * Carga los módulos dinámicamente
 */

(function() {
    'use strict';

    // Lista de módulos a cargar en orden
    var modules = [
        'static/js/search/constants.js',
        'static/js/search/state.js',
        'static/js/search/utils.js',
        'static/js/search/categories.js',
        'static/js/search/tabs.js',
        'static/js/search/search.js',
        'static/js/search/downloads.js',
        'static/js/search/modal.js',
        'static/js/search/polling.js',
        'static/js/search/main.js'
    ];

    var loadedCount = 0;
    var failedModules = [];

    function loadModule(url) {
        return new Promise(function(resolve, reject) {
            var script = document.createElement('script');
            script.src = url;
            script.onload = function() {
                console.log('[Search] Módulo cargado: ' + url);
                resolve();
            };
            script.onerror = function() {
                console.error('[Search] Error cargando módulo: ' + url);
                failedModules.push(url);
                resolve(); // Resolvemos para continuar con otros módulos
            };
            document.head.appendChild(script);
        });
    }

    async function loadAllModules() {
        console.log('[Search] Iniciando carga de módulos...');
        
        for (var i = 0; i < modules.length; i++) {
            await loadModule(modules[i]);
        }

        if (failedModules.length > 0) {
            console.warn('[Search] Algunos módulos no se cargaron:', failedModules);
        }

        console.log('[Search] Todos los módulos procesados, disparando evento...');
        
        // Disparar evento cuando terminen de cargar
        var event = new CustomEvent('search-modules-loaded');
        document.dispatchEvent(event);
    }

    // Iniciar carga cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadAllModules);
    } else {
        loadAllModules();
    }

})();
