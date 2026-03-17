/**
 * Search Page - Downloads
 * Lógica de descargas de torrents
 */
(function() {
    'use strict';

    /**
     * Inicia una descarga desde URL directa
     */
    window.startUrlDownload = async function() {
        var urlInput = document.getElementById('torrent-url');
        var categorySelect = document.getElementById('category-select');
        
        if (!urlInput) return;
        
        var url = urlInput.value.trim();
        var category = categorySelect ? categorySelect.value : '';

        if (!url) {
            if (typeof window.showStatus === 'function') {
                window.showStatus('Por favor, introduce una URL de torrent', 'error');
            }
            return;
        }

        // Validar URL
        if (!url.startsWith('magnet:') && !url.startsWith('http')) {
            if (typeof window.showStatus === 'function') {
                window.showStatus('La URL debe ser magnet: o http(s)://', 'error');
            }
            return;
        }

        await window.startDownload(url, '', category);
    };

    /**
     * Inicia la descarga de un torrent
     */
    window.startDownload = async function(url, resultId, category) {
        // Usar la categoría seleccionada si no se proporciona
        var categorySelect = document.getElementById('category-select');
        var selectedCategory = category || (categorySelect ? categorySelect.value : '');

        if (typeof window.showStatus === 'function') {
            window.showStatus('Iniciando descarga...', 'loading');
        }

        try {
            var endpoint = window.SEARCH_CONFIG ? window.SEARCH_CONFIG.endpoints.downloadTorrent : '/api/download-torrent';
            var response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: url,
                    result_id: resultId,
                    category: selectedCategory
                })
            });

            var data = await response.json();

            if (data.success) {
                if (typeof window.showStatus === 'function') {
                    window.showStatus('Descarga iniciada correctamente', 'success');
                }

                // Abrir modal de progreso
                if (typeof window.openDownloadModal === 'function') {
                    window.openDownloadModal(data.download, selectedCategory);
                }

                // Iniciar polling de progreso
                if (typeof window.startProgressPolling === 'function') {
                    window.startProgressPolling(data.download.torrent_id);
                }
            } else {
                if (typeof window.showStatus === 'function') {
                    window.showStatus(data.error || 'Error al iniciar la descarga', 'error');
                }
            }
        } catch (error) {
            console.error('Error iniciando descarga:', error);
            if (typeof window.showStatus === 'function') {
                window.showStatus('Error de conexión al iniciar la descarga', 'error');
            }
        }
    };

})();
