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
    $.getJSON('/status')
        .done(function (data) {
            console.log('✅ Datos recibidos:', data);

            const currentVideo = data.current_video || 'Ninguno';
            $('#currentFile').text(currentVideo);

            // Actualizar estadísticas
            $('#stat-frames').text(data.frames || '–');
            $('#stat-fps').text(data.fps || '–');
            $('#stat-time').text(data.time || '–');
            $('#stat-speed').text(data.speed || '–');

            // Parsear tiempo para progreso
            if (data.time) {
                const timeParts = data.time.split(':');
                if (timeParts.length === 3) {
                    let seconds = parseInt(timeParts[0]) * 3600 +
                        parseInt(timeParts[1]) * 60 +
                        parseInt(timeParts[2]);

                    // Si tenemos duración, calcular progreso
                    const durationStr = $('#info-duration').text();
                    if (durationStr && durationStr !== '–') {
                        const durParts = durationStr.split(':');
                        if (durParts.length === 3) {
                            let totalSeconds = parseInt(durParts[0]) * 3600 +
                                parseInt(durParts[1]) * 60 +
                                parseInt(durParts[2]);

                            if (totalSeconds > 0 && seconds > 0) {
                                let progress = Math.min(100, Math.round((seconds / totalSeconds) * 100));
                                $('#progressBar').css('width', progress + '%');
                                $('#progressText').text(`Procesando: ${progress}% (${data.time})`);
                            }
                        }
                    } else {
                        // Si no hay duración, mostrar tiempo transcurrido
                        $('#progressText').text(`Procesando: ${data.time}`);
                    }
                }
            }

            // Actualizar icono
            let emoji = '🟢';
            const logLine = (data.log_line || '').toLowerCase();
            if (logLine.includes('error')) emoji = '❌';
            else if (logLine.includes('completado')) emoji = '✅';
            else if (data.frames > 0) emoji = '⏳';
            $('#statusIcon').text(emoji);
        })
        .fail(function (xhr, status, error) {
            console.error('❌ Error consultando status:', error);
        });
}

// Exportar
window.optimizerProgress = {
    startMonitoring,
    stopMonitoring
};