/**
 * Profile Page - Watchlist Modal
 * Gestión del modal de watchlist
 */
(function() {
    'use strict';

    /**
     * Muestra el modal de watchlist
     */
    window.showWatchlistModal = function() {
        var modal = document.getElementById('watchlistModal');
        var overlay = document.getElementById('modalOverlay');
        
        // Cerrar dropdown
        var menu = document.getElementById('profileMenu');
        if (menu) menu.classList.remove('show');
        
        if (modal) modal.style.display = 'block';
        if (overlay) overlay.style.display = 'block';
    };

    /**
     * Cierra el modal de watchlist
     */
    window.closeWatchlistModal = function() {
        var modal = document.getElementById('watchlistModal');
        var overlay = document.getElementById('modalOverlay');
        
        if (modal) modal.style.display = 'none';
        if (overlay) overlay.style.display = 'none';
    };

})();
