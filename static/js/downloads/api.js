/**
 * Downloads - API Service
 */

const DownloadsAPI = {
    async getActiveDownloads() {
        const response = await fetch(CONFIG.endpoints.downloadsActive);
        return response.json();
    },

    async getDownloadStatus(id) {
        const response = await fetch(CONFIG.endpoints.downloadStatus(id));
        return response.json();
    },

    async cancelDownload(id) {
        const response = await fetch(CONFIG.endpoints.downloadCancel(id), { method: 'POST' });
        return response.json();
    },

    async removeDownload(id) {
        const response = await fetch(CONFIG.endpoints.downloadRemove(id), { method: 'POST' });
        return response.json();
    },

    async startTorrentOptimize(data) {
        const response = await fetch(CONFIG.endpoints.torrentOptimizeStart, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async getActiveOptimizations() {
        const response = await fetch(CONFIG.endpoints.torrentOptimizeActive);
        return response.json();
    },

    async getOptimizationStatus(id) {
        const response = await fetch(CONFIG.endpoints.torrentOptimizeStatus(id));
        return response.json();
    },

    async getOptimizationHistory() {
        const response = await fetch(CONFIG.endpoints.optimizationHistory);
        return response.json();
    },

    async getLatestOptimizations() {
        const response = await fetch(CONFIG.endpoints.optimizationHistoryLatest);
        return response.json();
    }
};

window.DownloadsAPI = DownloadsAPI;
