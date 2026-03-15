/**
 * Admin Panel - State
 */

let statsData = null;
let loadingTimeout = null;

function getStatsData() {
    return statsData;
}

function setStatsData(data) {
    statsData = data;
}

function setLoadingTimeout(timeout) {
    loadingTimeout = timeout;
}

function getLoadingTimeout() {
    return loadingTimeout;
}
