/**
 * Downloads - Polling Manager
 */

const PollingManager = {
    interval: null,
    isPolling: false,

    start(pollFn, interval = CONFIG.pollInterval) {
        if (this.isPolling) return;

        this.isPolling = true;
        this.interval = setInterval(pollFn, interval);
        pollFn();
    },

    stop() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
        this.isPolling = false;
    },

    restart(pollFn, interval) {
        this.stop();
        this.start(pollFn, interval);
    }
};

async function startPolling() {
    if (state.isPolling) return;

    state.isPolling = true;

    PollingManager.start(async () => {
        const activeTab = state.activeTab;

        if (activeTab === 'downloads') {
            await refreshDownloads();
        } else if (activeTab === 'optimizations') {
            await refreshOptimizations();
        }
    });
}

function stopPolling() {
    PollingManager.stop();
    state.isPolling = false;
}

async function refreshDownloads() {
    try {
        const data = await DownloadsAPI.getActiveDownloads();
        if (data.downloads) {
            state.downloads = data.downloads;
            state.activeDownloadsCount = data.downloads.length;
            renderDownloadsList(data.downloads);
            updateActiveCount();
        }
    } catch (error) {
        console.error('Error refreshing downloads:', error);
    }
}

async function refreshOptimizations() {
    try {
        const data = await DownloadsAPI.getActiveOptimizations();
        if (data.optimizations) {
            state.optimizations = data.optimizations;
            renderOptimizationsList(data.optimizations);
        }
    } catch (error) {
        console.error('Error refreshing optimizations:', error);
    }
}

async function loadHistory() {
    try {
        const data = await DownloadsAPI.getLatestOptimizations();
        if (data.history) {
            state.history = data.history;
            renderHistoryList(data.history);
        }
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

function updateActiveCount() {
    const badge = document.getElementById('active-downloads-badge');
    if (badge) {
        badge.textContent = state.activeDownloadsCount;
        badge.style.display = state.activeDownloadsCount > 0 ? 'inline' : 'none';
    }
}

window.startPolling = startPolling;
window.stopPolling = stopPolling;
window.refreshDownloads = refreshDownloads;
window.refreshOptimizations = refreshOptimizations;
window.loadHistory = loadHistory;
