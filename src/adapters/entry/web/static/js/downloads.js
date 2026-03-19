/**
 * Downloads Page - JavaScript para la página unificada de descargas y optimización
 * Maneja búsqueda, descargas, optimizaciones y historial
 * 
 * Este archivo ahora carga los módulos separados para mantener compatibilidad
 * con el HTML existente
 */

(function() {
    'use strict';
    
    // Determinar la ruta base correcta
    // Si estamos en /static/js/downloads.js, la base es /static/js/
    var basePath = '/static/js/';
    
    // Lista de módulos a cargar en orden (con rutas absolutas)
    var moduleFiles = [
        basePath + 'downloads/constants.js',
        basePath + 'downloads/state.js', 
        basePath + 'downloads/utils.js',
        basePath + 'downloads/filters.js',
        basePath + 'downloads/tabs.js',
        basePath + 'downloads/api.js',
        basePath + 'downloads/ui.js',
        basePath + 'downloads/downloads.js',
        basePath + 'downloads/optimizations.js',
        basePath + 'downloads/history.js',
        basePath + 'downloads/main.js'
    ];
    
    var loadedCount = 0;
    
    function onModuleLoaded() {
        loadedCount++;
        if (loadedCount === moduleFiles.length) {
            console.log('[Downloads] Todos los módulos cargados correctamente');
            // Disparar evento para que otros scripts sepan que ya está todo listo
            document.dispatchEvent(new CustomEvent('downloads-modules-loaded', { 
                detail: { modules: moduleFiles } 
            }));
        }
    }
    
    function loadModules() {
        console.log('[Downloads] Cargando módulos desde:', basePath);
        
        moduleFiles.forEach(function(file) {
            var script = document.createElement('script');
            script.src = file;
            script.onload = onModuleLoaded;
            script.onerror = function() {
                console.error('[Downloads] Error cargando módulo:', file);
                // Intentar con ruta alternativa (por si acaso)
                var altScript = document.createElement('script');
                altScript.src = file.replace('/static/js/', '/static/js/downloads/');
                altScript.onload = onModuleLoaded;
                altScript.onerror = function() {
                    console.error('[Downloads] También falló la ruta alternativa:', altScript.src);
                    onModuleLoaded(); // Continuar aunque falle
                };
                document.head.appendChild(altScript);
            };
            document.head.appendChild(script);
        });
    }
    
    // Cargar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadModules);
    } else {
        loadModules();
    }
    
})();