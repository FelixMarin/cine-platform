// status.js - Versión corregida

let isProcessing = false;
let userInitiatedProcess = false;

function setProcessing(value) {
    isProcessing = value;
}

function setUserInitiated(value) {
    userInitiatedProcess = value;
}

function updateStatus() {
    $.getJSON('/status', function (data) {
        const currentVideo = data.current_video || null;

        // SI HAY SUBIDA EN CURSO, IGNORAR ESTADO
        if (window.optimizerUpload && window.optimizerUpload.isUploading()) {
            console.log('⏳ Subida en curso, ignorando status');
            return;
        }

        // SOLO actualizar la información si hay un proceso activo iniciado por el usuario
        if (currentVideo && userInitiatedProcess) {
            $('#currentFile').text(currentVideo);

            const resumen = data.log_line || '';
            const campos = {};

            if (resumen.includes('|')) {
                resumen.split('|').forEach(part => {
                    const [key, value] = part.split('=').map(s => s.trim());
                    if (key && value) campos[key.toLowerCase()] = value;
                });
            }

            $('#stat-frames').text(campos['frames'] || '–');
            $('#stat-fps').text(campos['fps'] || '–');
            $('#stat-time').text(campos['time']?.split('.')[0] || '–');
            $('#stat-bitrate').text(campos['bitrate'] || '–');
            $('#stat-speed').text(campos['speed'] || '–');

            const info = data.video_info || {};
            const durSeg = info.duration ? info.duration.split(' ')[0] : null;
            $('#info-duration').text(durSeg ? window.optimizerUtils.formatSecondsToHHMMSS(durSeg) : '–');
            $('#info-name').text(info.name || '–');
            $('#info-resolution').text(info.resolution || '–');
            $('#info-format').text(info.format || '–');
            $('#info-vcodec').text(info.vcodec || '–');
            $('#info-acodec').text(info.acodec || '–');
            $('#info-size').text(info.size || '–');

            if (!isProcessing) {
                isProcessing = true;
                window.optimizerUI.showProgressSection();
                window.optimizerProgress.startMonitoring();
            }
        } else if (!currentVideo && isProcessing && !window.optimizerUpload?.isUploading()) {
            // Solo resetear si NO hay subida en curso
            window.optimizerUI.resetAfterCompletion('sin video');
        }
    }).fail(function () {
        console.log('Error conectando con el servidor');
    });
}

// Exportar
window.optimizerStatus = {
    setProcessing,
    setUserInitiated,
    updateStatus
};