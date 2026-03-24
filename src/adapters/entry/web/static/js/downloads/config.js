/**
 * Configuration for Downloads page
 */

const CONFIG = {
    pollInterval: 3000,
    maxHistoryItems: 50,
    endpoints: {
        search: '/api/search-movie',
        downloadTorrent: '/api/download-torrent',
        downloadUrl: '/api/download-url',
        downloadsActive: '/api/downloads/active',
        downloadStatus: (id) => `/api/downloads/${id}/status`,
        downloadCancel: (id) => `/api/downloads/${id}/cancel`,
        downloadStop: (id) => `/api/download-stop/${id}`,
        downloadStart: (id) => `/api/download-start/${id}`,
        downloadRemove: (id) => `/api/download-remove/${id}`,
        optimizeStart: '/api/optimizer/optimize',
        optimizeStatus: '/api/optimizer/status',
        optimizeCancel: '/api/optimizer/cancel',
        optimizeProfiles: '/api/optimizer/profiles',
        torrentOptimizeActive: '/api/optimize-torrent/active',
        torrentOptimizeStatus: (id) => `/api/optimize-torrent/status/${id}`,
        torrentOptimizeStart: '/api/optimize-torrent',
        optimizationHistory: '/api/optimization-history/',
        optimizationHistoryLatest: '/api/optimization-history/latest'
    }
};
