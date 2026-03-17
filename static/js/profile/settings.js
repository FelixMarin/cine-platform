/**
 * Profile Page - Settings Modal
 * Gestión del modal de configuración
 */
(function() {
    'use strict';

    /**
     * Muestra el modal de configuración
     */
    window.showSettingsModal = function() {
        var modal = document.getElementById('settingsModal');
        var overlay = document.getElementById('modalOverlay');
        
        // Cerrar dropdown
        var menu = document.getElementById('profileMenu');
        if (menu) menu.classList.remove('show');
        
        if (modal) modal.style.display = 'block';
        if (overlay) overlay.style.display = 'block';
    };

    /**
     * Cierra el modal de configuración
     */
    window.closeSettingsModal = function() {
        var modal = document.getElementById('settingsModal');
        var overlay = document.getElementById('modalOverlay');
        
        if (modal) modal.style.display = 'none';
        if (overlay) overlay.style.display = 'none';
    };

})();
