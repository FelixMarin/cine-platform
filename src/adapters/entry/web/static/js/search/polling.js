/**
 * Search Page - Polling
 * Polling de progreso de descarga
 */
(function() {
    'use strict';

    /**
     * Inicia el polling de progreso de descarga
     */
    window.startProgressPolling = function(torrentId) {
        // Detener cualquier polling anterior
        if (window.searchState.downloadInterval) {
            clearInterval(window.searchState.downloadInterval);
        }

        var interval = window.SEARCH_CONFIG ? window.SEARCH_CONFIG.pollInterval : 2000;

        // Actualizar cada 2 segundos
        window.searchState.downloadInterval = setInterval(async function() {
            await window.updateDownloadProgress(torrentId);
        }, interval);
    };

    /**
     * Actualiza el progreso de descarga
     */
    window.updateDownloadProgress = async function(torrentId) {
        try {
            var endpoint = window.SEARCH_CONFIG ? window.SEARCH_CONFIG.endpoints.downloadsActive : '/api/download-status';
            var response = await fetch(endpoint + '?status=active');
            var data = await response.json();

            if (data.success && data.downloads) {
                // Buscar el torrent específico
                var torrent = data.downloads.find(function(d) {
                    return d.id === torrentId || d.torrent_id === torrentId;
                });

                if (torrent) {
                    window.updateProgressUI(torrent);
                }
            }
        } catch (error) {
            console.error('Error actualizando progreso:', error);
        }
    };

    /**
     * Actualiza la UI con el progreso
     */
    window.updateProgressUI = function(torrent) {
        var progress = torrent.progress || 0;
        var progressBar = document.getElementById('progress-bar');
        var progressText = document.getElementById('progress-text');
        var speedEl = document.getElementById('download-speed');
        var etaEl = document.getElementById('download-eta');

        // Actualizar barra
        if (progressBar) {
            progressBar.style.width = progress + '%';
        }
        if (progressText) {
            progressText.textContent = progress.toFixed(1) + '%';
        }

        // Actualizar velocidad
        if (speedEl && torrent.rate_download > 0) {
            var speed = window.formatSpeed ? window.formatSpeed(torrent.rate_download) : torrent.rate_download;
            speedEl.textContent = 'Velocidad: ' + speed;
        }

        // Actualizar tiempo restante
        if (etaEl) {
            if (torrent.eta > 0 && torrent.eta < 31536000) {  // Menos de 1 año
                etaEl.textContent = 'Tiempo restante: ' + torrent.eta_formatted;
            } else if (torrent.progress >= 100) {
                etaEl.textContent = 'Completado';
                // Detener polling cuando termine
                if (window.searchState.downloadInterval) {
                    clearInterval(window.searchState.downloadInterval);
                    window.searchState.downloadInterval = null;
                }
            } else {
                etaEl.textContent = 'Tiempo restante: Calculando...';
            }
        }
    };

})();
