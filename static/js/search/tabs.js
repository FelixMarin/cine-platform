/**
 * Search Page - Tabs Management
 * Gestión de modos de búsqueda (tabs)
 */
(function() {
    'use strict';

    /**
     * Maneja la tecla Enter en el input de búsqueda
     */
    window.handleSearchKeypress = function(event) {
        if (event.key === 'Enter') {
            if (typeof window.performSearch === 'function') {
                window.performSearch();
            }
        }
    };

})();
