/**
 * Profile Page - Utilities
 * Funciones de utilidad: escapeHtml, closeAllModals
 */
(function() {
    'use strict';

    /**
     * Escapa HTML para prevenir XSS
     */
    window.escapeHtml = function(text) {
        if (!text) return '';
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };

    /**
     * Cierra todos los modales de la página de perfil
     */
    window.closeAllModals = function() {
        var profileModal = document.getElementById('profileModal');
        var settingsModal = document.getElementById('settingsModal');
        var watchlistModal = document.getElementById('watchlistModal');
        var modalOverlay = document.getElementById('modalOverlay');
        
        if (profileModal) profileModal.style.display = 'none';
        if (settingsModal) settingsModal.style.display = 'none';
        if (watchlistModal) watchlistModal.style.display = 'none';
        if (modalOverlay) modalOverlay.style.display = 'none';
    };

})();
