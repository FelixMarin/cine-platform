// utils.js - Funciones de utilidad

function formatSecondsToHHMMSS(seconds) {
    seconds = parseInt(seconds, 10);
    if (isNaN(seconds)) return '–';

    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return [h, m, s].map(v => String(v).padStart(2, '0')).join(':');
}

function updateStatusIcon(logLine) {
    const $icon = $('#statusIcon');
    const line = logLine || '';

    let emoji = '🟢';

    if (line.toLowerCase().includes('error')) {
        emoji = '❌';
    } else if (line.toLowerCase().includes('completed')) {
        emoji = '✅';
    } else if (line.toLowerCase().includes('frame') || line.toLowerCase().includes('fps')) {
        emoji = '⏳';
    }

    $icon.text(emoji);
}

// Exportar funciones al ámbito global
window.optimizerUtils = {
    formatSecondsToHHMMSS,
    updateStatusIcon
};