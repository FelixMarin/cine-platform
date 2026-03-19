/**
 * PROFILE.JS - Punto de entrada para la página de perfil
 * Carga los módulos dinámicamente
 */

(function() {
    'use strict';

    // Lista de módulos a cargar en orden
    var modules = [
        'static/js/profile/constants.js',
        'static/js/profile/state.js',
        'static/js/profile/utils.js',
        'static/js/profile/api.js',
        'static/js/profile/menu.js',
        'static/js/profile/profile.js',
        'static/js/profile/avatar.js',
        'static/js/profile/settings.js',
        'static/js/profile/watchlist.js',
        'static/js/profile/main.js'
    ];

    var loadedCount = 0;
    var failedModules = [];

    function loadModule(url) {
        return new Promise(function(resolve, reject) {
            var script = document.createElement('script');
            script.src = url;
            script.onload = function() {
                console.log('[Profile] Módulo cargado: ' + url);
                resolve();
            };
            script.onerror = function() {
                console.error('[Profile] Error cargando módulo: ' + url);
                failedModules.push(url);
                resolve(); // Resolvemos para continuar con otros módulos
            };
            document.head.appendChild(script);
        });
    }

    async function loadAllModules() {
        console.log('[Profile] Iniciando carga de módulos...');
        
        for (var i = 0; i < modules.length; i++) {
            await loadModule(modules[i]);
        }

        if (failedModules.length > 0) {
            console.warn('[Profile] Algunos módulos no se cargaron:', failedModules);
        }

        console.log('[Profile] Todos los módulos procesados, disparando evento...');
        
        // Disparar evento cuando terminen de cargar
        var event = new CustomEvent('profile-modules-loaded');
        document.dispatchEvent(event);
    }

    // Iniciar carga cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadAllModules);
    } else {
        loadAllModules();
    }

})();
