/**
 * Spanish content filter for Downloads page - VERSIÓN CON EXCLUSIÓN LATINA
 */

// Patrones de ESPAÑOL (lo que queremos incluir)
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

// Patrones de EXCLUSIÓN (lo que NO queremos - contenido latino)
const EXCLUDED_PATTERNS = [
    // Latino explícito
    /latin/i,
    /latino/i,
    /\[lat\]/i,
    /\(lat\)/i,
    /\blat\b/i,
    
    // Combinaciones latinas (estas anulan el español)
    /spanish\s+latin/i,
    /latin\s+spanish/i,
    /esp\s+lat/i,
    /lat\s+esp/i,
    /spanish\s+latino/i,
    /latino\s+spanish/i,
    
    // Versiones latinas específicas
    /brrip\s+latin/i,
    /webrip\s+latin/i,
    /bluray\s+latin/i,
    /hdrip\s+latin/i,
    /dvdrip\s+latin/i,
    
    // Países latinos (indican versión de ese país)
    /mexican/i,
    /mexico/i,
    /argentina/i,
    /colombia/i,
    /chile/i,
    /peru/i,
    /venezuela/i,
    
    // Audio latino
    /audio\s+latin/i,
    /doblaje\s+latin/i,
    /castellano\s+latin/i
];

function isSpanishContent(result) {
    if (!result) return false;
    
    const searchText = [
        result.title,
        result.fullTitle,
        result.description
    ].filter(Boolean).join(' ').toLowerCase();
    
    if (!searchText) return false;
    
    // PASO 1: Verificar si tiene algún patrón de EXCLUSIÓN (LATIN, etc.)
    for (const pattern of EXCLUDED_PATTERNS) {
        if (pattern.test(searchText)) {
            console.log(`❌ EXCLUIDO (${pattern}): ${result.title}`);
            return false; // Es latino, lo excluimos
        }
    }
    
    // PASO 2: Si no es latino, verificar si tiene algún patrón de ESPAÑOL
    for (const pattern of SPANISH_PATTERNS) {
        if (pattern.test(searchText)) {
            console.log(`✅ INCLUIDO (${pattern}): ${result.title}`);
            return true; // Es español y no es latino
        }
    }
    
    // PASO 3: Si no tiene ningún marcador de español, rechazar
    console.log(`❌ RECHAZADO (sin marcador español): ${result.title}`);
    return false;
}

function filterSpanishResults(results) {
    if (!results || !Array.isArray(results)) return [];
    console.log(`🔍 Filtrando ${results.length} resultados...`);
    
    const filtered = results.filter(result => isSpanishContent(result));
    
    console.log(`📊 Resultados después del filtro: ${filtered.length}`);
    return filtered;
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

// Exportar a window para acceso global
window.isSpanishContent = isSpanishContent;
window.filterSpanishResults = filterSpanishResults;
window.toggleSpanishFilter = toggleSpanishFilter;
window.applySpanishFilter = applySpanishFilter;