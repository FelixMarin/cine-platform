/**
 * Estado global del módulo de descargas
 */
(function() {
    'use strict';
    window.state = {
        activeTab: 'search', downloads: [], activeDownloadsCount: 0,
        optimizations: [], history: [], isPolling: false,
        searchResults: [], originalSearchResults: [], spanishFilterEnabled: true, pollIntervalId: null
    };
    window.historyData = []; window.historyCurrentPage = 1; window.historyTotalEntries = 0; window.HISTORY_PER_PAGE = 20;
    window.getState = function() { return window.state; };
    window.setState = function(k, v) { window.state[k] = v; };
    window.getDownloads = function() { return window.state.downloads; };
    window.setDownloads = function(d) { window.state.downloads = d; };
    window.getOptimizations = function() { return window.state.optimizations; };
    window.setOptimizations = function(o) { window.state.optimizations = o; };
    window.getActiveTab = function() { return window.state.activeTab; };
    window.setActiveTab = function(t) { window.state.activeTab = t; };
    window.getSearchResults = function() { return window.state.searchResults; };
    window.setSearchResults = function(r) { window.state.searchResults = r; };
    window.getOriginalSearchResults = function() { return window.state.originalSearchResults; };
    window.setOriginalSearchResults = function(r) { window.state.originalSearchResults = r; };
    window.isSpanishFilterEnabled = function() { return window.state.spanishFilterEnabled; };
    window.setSpanishFilterEnabled = function(e) { window.state.spanishFilterEnabled = e; };
    window.getOptimizationState = function(tid) {
        if (!window.state.optimizations || !tid) return null;
        var r = window.state.optimizations.find(function(o) { return o.torrent_id == tid || o.torrent_id === tid; });
        return r || null;
    };
    window.hasActiveOptimization = function(tid) {
        var o = window.getOptimizationState(tid); if (!o) return false;
        return ['running','starting','copying','pending'].includes(o.status);
    };
    window.hasCompletedOptimization = function(tid) {
        var o = window.getOptimizationState(tid); return o && o.status === 'completed';
    };
    window.getOptimizationError = function(tid) {
        var o = window.getOptimizationState(tid); return o ? o.error : null;
    };
})();
