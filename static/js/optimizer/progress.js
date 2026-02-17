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

// En progress.js, añade esta función para renderizar el historial

function renderHistory(history) {
    const $historyBody = $('#history');
    $historyBody.empty();

    if (!history || history.length === 0) {
        $historyBody.append('<tr><td colspan="6" class="text-center text-muted">No hay historial de procesamiento</td></tr>');
        return;
    }

    // Mostrar los últimos 10 registros (los más recientes primero)
    history.slice(-10).reverse().forEach(item => {
        // Determinar clase de estado
        let statusClass = '';
        let statusText = item.status || 'Desconocido';

        if (statusText.toLowerCase().includes('error')) {
            statusClass = 'status-error';
            statusText = '❌ ' + statusText;
        } else if (statusText.toLowerCase().includes('completado') ||
            statusText.toLowerCase().includes('procesado correctamente')) {
            statusClass = 'status-success';
            statusText = '✅ ' + statusText;
        } else {
            statusText = '⚠️ ' + statusText;
        }

        // Formatear duración
        let duration = item.duration || '–';
        if (typeof duration === 'number' || !isNaN(parseFloat(duration))) {
            const seconds = parseFloat(duration);
            if (seconds < 60) {
                duration = seconds.toFixed(1) + 's';
            } else if (seconds < 3600) {
                duration = Math.floor(seconds / 60) + 'm ' + Math.floor(seconds % 60) + 's';
            } else {
                duration = Math.floor(seconds / 3600) + 'h ' + Math.floor((seconds % 3600) / 60) + 'm';
            }
        }

        // Obtener perfil (si existe)
        const profile = item.profile || '–';

        // Crear fila
        const row = $(`
            <tr>
                <td>${item.name || '–'}</td>
                <td><span class="badge badge-info">${profile}</span></td>
                <td class="${statusClass}">${statusText}</td>
                <td>${item.timestamp || '–'}</td>
                <td>${duration}</td>
                <td>${item.size || '–'}</td>
            </tr>
        `);

        $historyBody.append(row);
    });
}

// Y modifica updateProgressBar para llamar a renderHistory:

function updateProgressBar() {
    $.getJSON('/status')
        .done(function (data) {
            console.log('✅ Datos recibidos:', data);

            const currentVideo = data.current_video || 'Ninguno';
            $('#currentFile').text(currentVideo);

            // Parsear el log_line para extraer estadísticas
            const logLine = data.log_line || '';

            // Extraer frames
            const frameMatch = logLine.match(/frames?[=:]?\s*(\d+)/i);
            const frames = frameMatch ? frameMatch[1] : '–';

            // Extraer fps
            const fpsMatch = logLine.match(/fps[=:]?\s*([\d.]+)/i);
            const fps = fpsMatch ? fpsMatch[1] : '–';

            // Extraer time
            const timeMatch = logLine.match(/time[=:]?\s*([\d:]+)/i);
            const time = timeMatch ? timeMatch[1] : '–';

            // Extraer bitrate
            const bitrateMatch = logLine.match(/bitrate[=:]?\s*([\d.]+k?)/i);
            const bitrate = bitrateMatch ? bitrateMatch[1] : '–';

            // Extraer speed
            const speedMatch = logLine.match(/speed[=:]?\s*([\d.]+)x/i);
            const speed = speedMatch ? speedMatch[1] + 'x' : '–';

            // Actualizar tabla de estadísticas
            $('#stat-frames').text(frames);
            $('#stat-fps').text(fps);
            $('#stat-time').text(time);
            $('#stat-bitrate').text(bitrate);
            $('#stat-speed').text(speed);

            // Actualizar información del video original
            const videoInfo = data.video_info || {};
            $('#info-name').text(videoInfo.name || '–');
            $('#info-duration').text(videoInfo.duration || '–');
            $('#info-resolution').text(videoInfo.resolution || '–');
            $('#info-format').text(videoInfo.format || '–');
            $('#info-vcodec').text(videoInfo.vcodec || '–');
            $('#info-acodec').text(videoInfo.acodec || '–');
            $('#info-size').text(videoInfo.size || '–');

            // RENDERIZAR HISTORIAL
            renderHistory(data.history || []);

            // Calcular progreso si tenemos time
            if (time !== '–') {
                const timeParts = time.split(':');
                if (timeParts.length === 3) {
                    let seconds = parseInt(timeParts[0]) * 3600 +
                        parseInt(timeParts[1]) * 60 +
                        parseInt(timeParts[2]);

                    const durationStr = videoInfo.duration || $('#info-duration').text();
                    if (durationStr && durationStr !== '–') {
                        const durParts = durationStr.split(':');
                        if (durParts.length === 3) {
                            let totalSeconds = parseInt(durParts[0]) * 3600 +
                                parseInt(durParts[1]) * 60 +
                                parseInt(durParts[2]);

                            if (totalSeconds > 0 && seconds > 0) {
                                let progress = Math.min(100, Math.round((seconds / totalSeconds) * 100));
                                $('#progressBar').css('width', progress + '%');
                                $('#progressText').text(`Procesando: ${progress}% (${time} / ${durationStr})`);
                            }
                        }
                    }
                }
            }

            // Actualizar icono
            let emoji = '🟢';
            if (logLine.toLowerCase().includes('error')) emoji = '❌';
            else if (logLine.toLowerCase().includes('completado')) emoji = '✅';
            else if (frames !== '–') emoji = '⏳';
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