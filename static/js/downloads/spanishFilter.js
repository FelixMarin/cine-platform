/**
 * Spanish content filter for Downloads page
 */

const SPANISH_PATTERNS = [
    /\[esp\]/i,
    /\[español\]/i,
    /\[spanish\]/i,
    /\[castellano\]/i,
    /\bespañol\b/i,
    /\bspanish\b/i,
    /\bcastellano\b/i,
    /\bsubtitulado\b/i,
    /\bvo\b/i,
    /\bversión original\b/i,
    /\bsp\./i,
    /\besp\./i,
    /\bes(-)?es\b/i,
    /\bes(-)?la\b/i,
    /\baudio español\b/i,
    /\baudio spanish\b/i,
    /\bdoblado\b/i,
    /\bdubbed\b/i,
    /\bdub\b/i
];

function isSpanishContent(result) {
    if (!result) return false;
    
    const searchText = [
        result.title,
        result.fullTitle,
        result.description
    ].filter(Boolean).join(' ').toLowerCase();
    
    if (!searchText) return false;
    
    for (const pattern of SPANISH_PATTERNS) {
        if (pattern.test(searchText)) {
            return true;
        }
    }
    
    return false;
}

function filterSpanishResults(results) {
    if (!results || !Array.isArray(results)) return [];
    return results.filter(result => isSpanishContent(result));
}

function toggleSpanishFilter() {
    const s = getState();
    s.spanishFilterEnabled = !s.spanishFilterEnabled;
    
    const checkbox = document.getElementById('spanish-filter-checkbox');
    if (checkbox) {
        checkbox.checked = s.spanishFilterEnabled;
    }
    
    renderSearchResults(s.originalSearchResults);
}

function applySpanishFilter(results) {
    const s = getState();
    if (s.spanishFilterEnabled) {
        return filterSpanishResults(results);
    }
    return results;
}
