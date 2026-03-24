/**
 * Search Page - Constants and Configuration
 * URLs y configuración para la búsqueda
 */
(function() {
    'use strict';

    window.SEARCH_CONFIG = {
        pollInterval: 2000,
        maxResults: 20,
        endpoints: {
            categories: '/api/categories',
            checkConnection: '/status',
            search: '/api/search-movie',
            downloadTorrent: '/api/download-torrent',
            downloadUrl: '/api/download-url',
            downloadsActive: '/api/downloads/active',
            downloadStatus: (id) => `/api/downloads/${id}/status`
        }
    };

})();
