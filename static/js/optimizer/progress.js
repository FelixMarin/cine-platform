// progress.js - Barra de progreso y monitoreo

let progressInterval = null;

function startMonitoring() {
    if (progressInterval) clearInterval(progressInterval);
    progressInterval = setInterval(updateProgressBar, 2000);
    updateProgressBar();
}

function stopMonitoring() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

function updateProgressBar() {
    $.getJSON('/status', function (data) {
        const logLine = data.log_line || '';
        const currentVideo = data.current_video || 'Ninguno';

        $('#currentFile').text(currentVideo);

        const stats = {};
        const frameMatch = logLine.match(/frames?[=:]?\s*(\d+)/i);
        if (frameMatch) stats.frames = frameMatch[1];

        const fpsMatch = logLine.match(/fps[=:]?\s*([\d.]+)/i);
        if (fpsMatch) stats.fps = fpsMatch[1];

        const timeMatch = logLine.match(/time[=:]?\s*([\d:]+)/i);
        if (timeMatch) stats.time = timeMatch[1];

        const speedMatch = logLine.match(/speed[=:]?\s*([\d.]+)x/i);
        if (speedMatch) stats.speed = speedMatch[1] + 'x';

        $('#stat-frames').text(stats.frames || '–');
        $('#stat-fps').text(stats.fps || '–');
        $('#stat-time').text(stats.time || '–');
        $('#stat-speed').text(stats.speed || '–');

        if (stats.time) {
            const timeParts = stats.time.split(':');
            let seconds = 0;
            if (timeParts.length === 3) {
                seconds = parseInt(timeParts[0]) * 3600 +
                    parseInt(timeParts[1]) * 60 +
                    parseInt(timeParts[2]);
            }

            const durationStr = $('#info-duration').text();
            let totalSeconds = 0;

            if (durationStr && durationStr !== '–') {
                const durParts = durationStr.split(':');
                if (durParts.length === 3) {
                    totalSeconds = parseInt(durParts[0]) * 3600 +
                        parseInt(durParts[1]) * 60 +
                        parseInt(durParts[2]);
                }
            }

            if (totalSeconds > 0 && seconds > 0) {
                const progress = Math.min(100, Math.round((seconds / totalSeconds) * 100));
                $('#progressBar').css('width', progress + '%').attr('aria-valuenow', progress);
                $('#progressText').text(`Procesando: ${progress}% completado (${stats.time} / ${durationStr})`);

                if (progress >= 100) {
                    setTimeout(window.optimizerUI.resetAfterCompletion, 3000);
                }
            } else {
                $('#progressBar').css('width', '50%');
            }
        } else {
            $('#progressBar').css('width', '50%');
        }

        window.optimizerUtils.updateStatusIcon(logLine);
    }).fail(() => console.log('Error conectando con el servidor'));
}

// Exportar
window.optimizerProgress = {
    startMonitoring,
    stopMonitoring
};