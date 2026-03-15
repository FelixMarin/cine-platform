/**
 * Global state for Downloads page
 */

const state = {
    activeTab: 'search',
    downloads: [],
    activeDownloadsCount: 0,
    optimizations: [],
    history: [],
    isPolling: false,
    searchResults: [],
    originalSearchResults: [],
    spanishFilterEnabled: true
};

function getState() {
    return state;
}

function setActiveTab(tabName) {
    state.activeTab = tabName;
}

function getActiveTab() {
    return state.activeTab;
}

function setSearchResults(results) {
    state.searchResults = results;
    state.originalSearchResults = [...results];
}

function getSearchResults() {
    return state.searchResults;
}

function setSpanishFilter(enabled) {
    state.spanishFilterEnabled = enabled;
}

function isSpanishFilterEnabled() {
    return state.spanishFilterEnabled;
}
