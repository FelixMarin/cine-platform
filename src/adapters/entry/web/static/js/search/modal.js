/**
 * Search Page - Modal
 * Modal de progreso de descarga
 */
(function() {
    'use strict';

    /**
     * Abre el modal de progreso de descarga
     */
    window.openDownloadModal = function(download, category) {
        var modal = document.getElementById('download-modal');
        var nameEl = document.getElementById('download-name');
        var categoryEl = document.getElementById('download-category');

        if (!modal || !nameEl) return;

        nameEl.textContent = download.name || 'Descarga';
        
        if (categoryEl) {
            categoryEl.textContent = category ? 'Categoría: ' + category : 'Sin categoría';
        }

        // Resetear progreso
        var progressBar = document.getElementById('progress-bar');
        var progressText = document.getElementById('progress-text');
        var speedEl = document.getElementById('download-speed');
        var etaEl = document.getElementById('download-eta');

        if (progressBar) progressBar.style.width = '0%';
        if (progressText) progressText.textContent = '0%';
        if (speedEl) speedEl.textContent = 'Velocidad: --';
        if (etaEl) etaEl.textContent = 'Tiempo restante: --';

        modal.style.display = 'flex';
        window.searchState.currentDownloadId = download.torrent_id;
    };

    /**
     * Cierra el modal de progreso
     */
    window.closeDownloadModal = function() {
        var modal = document.getElementById('download-modal');
        if (modal) {
            modal.style.display = 'none';
        }

        // Detener polling
        if (window.searchState.downloadInterval) {
            clearInterval(window.searchState.downloadInterval);
            window.searchState.downloadInterval = null;
        }

        window.searchState.currentDownloadId = null;
    };

    /**
     * Redirige a la página de descargas
     */
    window.viewDownloads = function() {
        window.closeDownloadModal();
        // Por ahora, simplemente actualizamos la página
        // Podría abrirse una pestaña de descargas
        window.location.href = '/';
    };

})();
