/**
 * Filtros de idioma español
 */
(function() {
    'use strict';
    window.isSpanishContent = function(r) {
        if (!r) return false;
        var t = [r.title, r.fullTitle, r.description].filter(Boolean).join(' ').toLowerCase();
        if (!t) return false;
        for (var i = 0; i < window.SPANISH_PATTERNS.length; i++) {
            if (window.SPANISH_PATTERNS[i].test(t)) return true;
        }
        return false;
    };
    window.filterSpanishResults = function(rs) {
        if (!rs || !Array.isArray(rs)) return [];
        return rs.filter(function(r) { return window.isSpanishContent(r); });
    };
    window.toggleSpanishFilter = function() {
        window.state.spanishFilterEnabled = !window.state.spanishFilterEnabled;
        var cb = document.getElementById('spanish-filter-checkbox');
        if (cb) cb.checked = window.state.spanishFilterEnabled;
        if (window.renderSearchResults) window.renderSearchResults(window.state.originalSearchResults);
    };
})();