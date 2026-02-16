// status.js - Polling de estado y actualización de UI

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
        } else {
            $('#currentFile').text('Ninguno');
            $('#stat-frames, #stat-fps, #stat-time, #stat-bitrate, #stat-speed').text('–');
            $('#info-name, #info-duration, #info-resolution, #info-format, #info-vcodec, #info-acodec, #info-size').text('–');
            $('#statusIcon').text('🟢');

            if (isProcessing) {
                window.optimizerUI.resetAfterCompletion();
            }
        }
    }).fail(() => console.log('Error conectando con el servidor'));
}

// Exportar
window.optimizerStatus = {
    setProcessing,
    setUserInitiated,
    updateStatus
};