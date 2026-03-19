/**
 * Search Page - Search Logic
 * Lógica de búsqueda y visualización de resultados
 */
(function() {
    'use strict';

    /**
     * Realiza la búsqueda de películas
     */
    window.performSearch = async function() {
        var queryInput = document.getElementById('search-query');
        if (!queryInput) return;
        
        var query = queryInput.value.trim();

        if (!query) {
            if (typeof window.showStatus === 'function') {
                window.showStatus('Por favor, introduce un término de búsqueda', 'error');
            }
            return;
        }

        if (typeof window.showStatus === 'function') {
            window.showStatus('Buscando...', 'loading');
        }

        try {
            var endpoint = window.SEARCH_CONFIG ? window.SEARCH_CONFIG.endpoints.search : '/api/search-movie';
            var limit = window.SEARCH_CONFIG ? window.SEARCH_CONFIG.maxResults : 20;
            var response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ q: query, limit: limit })
            });
            var data = await response.json();

            if (data.success) {
                window.displayResults(data.results, data.count);

                if (data.count === 0) {
                    if (typeof window.showStatus === 'function') {
                        window.showStatus('No se encontraron resultados para "' + query + '"', 'success');
                    }
                } else {
                    if (typeof window.showStatus === 'function') {
                        window.showStatus('Se encontraron ' + data.count + ' resultados', 'success');
                    }
                }
            } else {
                if (typeof window.showStatus === 'function') {
                    window.showStatus(data.error || 'Error en la búsqueda', 'error');
                }
                window.displayResults([], 0);
            }
        } catch (error) {
            console.error('Error en búsqueda:', error);
            if (typeof window.showStatus === 'function') {
                window.showStatus('Error de conexión durante la búsqueda', 'error');
            }
            window.displayResults([], 0);
        }
    };

    /**
     * Muestra los resultados en el grid
     */
    window.displayResults = function(results, count) {
        var container = document.getElementById('results-container');
        if (!container) return;

        if (!results || results.length === 0) {
            container.innerHTML = '<div class="no-results">' +
                '<div class="no-results-icon">🔍</div>' +
                '<h3>Sin resultados</h3>' +
                '<p>Intenta con otros términos de búsqueda</p>' +
                '</div>';
            return;
        }

        container.innerHTML = results.map(function(result) {
            var title = window.escapeHtml ? window.escapeHtml(result.title) : result.title;
            var guid = window.escapeHtml ? window.escapeHtml(result.guid) : result.guid;
            var indexer = window.escapeHtml ? window.escapeHtml(result.indexer) : result.indexer;
            // Usar download_url, magnet_url o torrent_url
            var url = window.escapeHtml ? window.escapeHtml(result.download_url || result.magnet_url || result.torrent_url || '') : result.download_url || result.magnet_url || result.torrent_url || '';
            var size = result.size_formatted || (window.formatSize ? window.formatSize(result.size) : result.size);
            
            var metaHtml = '<span class="result-meta-item size">💾 ' + size + '</span>';
            
            if (result.seeders) {
                metaHtml += '<span class="result-meta-item seeders">⬆️ ' + result.seeders + ' seeders</span>';
            }
            if (result.leechers) {
                metaHtml += '<span class="result-meta-item">⬇️ ' + result.leechers + ' leechers</span>';
            }
            if (result.publish_date) {
                metaHtml += '<span class="result-meta-item">📅 ' + result.publish_date + '</span>';
            }

            var hasUrl = result.download_url || result.magnet_url || result.torrent_url;
            var disabledAttr = !hasUrl ? 'disabled' : '';

            return '<div class="result-card" data-guid="' + guid + '">' +
                '<div class="result-header">' +
                '<h3 class="result-title" title="' + title + '">' + title + '</h3>' +
                '<span class="result-indexer">' + indexer + '</span>' +
                '</div>' +
                '<div class="result-meta">' + metaHtml + '</div>' +
                '<div class="result-actions">' +
                '<button class="btn-download" onclick="startDownload(\'' + url + '\', \'' + guid + '\')" ' + disabledAttr + '>' +
                '⬇️ Descargar' +
                '</button>' +
                '</div>' +
                '</div>';
        }).join('');
    };

})();
