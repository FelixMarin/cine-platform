$(document).ready(function () {

    // --- Vista previa del video ---
    $('#video-input').on('change', function () {
        const file = this.files[0];
        if (file) {
            const url = URL.createObjectURL(file);
            $('#video-preview').attr('src', url);
            $('#video-preview-container').fadeIn();
        } else {
            $('#video-preview-container').hide();
        }
    });

    // --- Lanzar procesamiento por ruta ---
    $('#startProcessing').click(function () {
        const folderPath = $('#folderPath').val().trim();
        if (!folderPath) {
            alert('Por favor, introduce una ruta válida.');
            return;
        }
        $.ajax({
            url: '/process',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ folder: folderPath }),
            success: function (resp) {
                console.log(resp.message);
            },
            error: function (xhr) {
                console.error(xhr.responseJSON ? xhr.responseJSON.error : "Error desconocido");
            }
        });
    });

    let currentUpload = null;

    // --- Subida de archivo real ---
    $('#upload-form').on('submit', function (e) {
        e.preventDefault();
        const fileInput = $('#video-input')[0];
        if (!fileInput.files.length) {
            alert('Selecciona un archivo primero.');
            return;
        }

        $('#upload-status').fadeIn();
        $('#cancel-upload-btn').hide();
        $('#status-text').text('Subiendo...');
        $('.progress-bar div').css('width', '0%');
        $('#upload-percent').text('0%');

        const formData = new FormData();
        formData.append('video', fileInput.files[0]);

        $.ajax({
            url: '/process-file',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            xhr: function () {
                let xhr = $.ajaxSettings.xhr();
                currentUpload = xhr;
                if (xhr.upload) {
                    xhr.upload.addEventListener('progress', function (evt) {
                        if (evt.lengthComputable) {
                            let percent = Math.round((evt.loaded / evt.total) * 100);
                            $('.progress-bar div').css('width', percent + '%');
                            $('#upload-percent').text(percent + '%');
                        }
                    }, false);
                }
                return xhr;
            },
            success: function (resp) {
                $('#status-text').text(resp.message);
                setTimeout(() => {
                    $('#upload-status').fadeOut();
                    $('#video-preview-container').fadeOut();
                    $('#upload-form')[0].reset();
                }, 2000);
            },
            error: function (xhr) {
                $('#status-text').text('Error en la subida');
                $('#cancel-upload-btn').show();
                console.error(xhr.responseJSON ? xhr.responseJSON.error : "Error desconocido");
            }
        });
    });

    function formatSecondsToHHMMSS(seconds) {
        seconds = parseInt(seconds, 10);
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;

        return [h, m, s]
            .map(unit => String(unit).padStart(2, '0'))
            .join(':');
    }

    // --- Actualización de estado cada 2s ---
    function updateStatus() {
        $.getJSON('/status', function (data) {
            // Actualiza el nombre del archivo
            $('#currentFile').text(data.current_file || data.current_video || 'Ninguno');

            // Extrae y muestra los valores en la tabla
            const resumen = data.log_line || '';
            const campos = {};

            if (resumen && resumen.includes('|')) {
                resumen.split('|').forEach(part => {
                    const [key, valueRaw] = part.split('=').map(s => s.trim());
                    if (key && valueRaw) campos[key.toLowerCase()] = valueRaw;
                });
            }

            $('#stat-frames').text(campos['frames'] || '–');
            $('#stat-fps').text(campos['fps'] || '–');
            $('#stat-time').text(campos['time'] ? campos['time'].split('.')[0] : '–');
            $('#stat-bitrate').text(campos['bitrate'] || '–');
            $('#stat-speed').text(campos['speed'] || '–');

            const info = data.video_info || {};
            const duracionSegundos = info.duration ? info.duration.split(' ')[0] : null;
            const duracionFormateada = duracionSegundos ? formatSecondsToHHMMSS(duracionSegundos) : '–';
            $('#info-duration').text(duracionFormateada);
            $('#info-name').text(info.name || '–');
            $('#info-resolution').text(info.resolution || '–');
            $('#info-format').text(info.format || '–');
            $('#info-vcodec').text(info.vcodec || '–');
            $('#info-acodec').text(info.acodec || '–');
            $('#info-size').text(info.size || '–');

            // Algunos campos pueden cambiar de nombre en diferentes versiones del servidor
            if (info.vcodec) $('#info-vcodec').text(info.vcodec);
            if (info.acodec) $('#info-acodec').text(info.acodec);

            // Actualiza los pasos e historial
            updateSteps(data.current_step);
            updateHistory(data.history);

            // Actualiza el icono de estado
            updateStatusIcon(data.log_line || '');
        });
    }

    function updateSteps(step) {
        $('.pipeline-step').removeClass('active completed').addClass('inactive');
        for (let i = 1; i < step; i++) {
            $('#step' + i).removeClass('inactive').addClass('completed');
        }
        if (step > 0 && step <= 4) {
            $('#step' + step).removeClass('inactive').addClass('active');
        }
    }

    function updateHistory(history) {
        $('#history').empty();
        history.forEach(item => {
            let name, status, timestamp, duration;
            if (Array.isArray(item)) {
                name = item[0];
                status = item[1];
                timestamp = item[2] || '–';
                duration = item[3] || '–';
            } else {
                name = item.name;
                status = item.status;
                timestamp = item.timestamp || '–';
                duration = item.duration || '–';
            }
            const statusClass = status.toLowerCase().includes('error') ? 'status-error' : 'status-success';
            $('#history').append(
                `<tr>
                    <td>${name}</td>
                    <td class="${statusClass}">${status}</td>
                    <td>${timestamp}</td>
                    <td>${duration}</td>
                </tr>`
            );
        });
    }

    function updateStatusIcon(logLine) {
        const iconElement = $('#statusIcon');
        const line = logLine || '';

        let icon = '🟡'; // Estado por defecto: en espera

        if (line.toLowerCase().includes('error') || line.toLowerCase().includes('failed')) {
            icon = '🔴'; // Error detectado
        } else if (line.toLowerCase().includes('frame') || line.toLowerCase().includes('speed')) {
            icon = '🟢'; // Procesando activamente
        } else if (line.toLowerCase().includes('completed') || line.toLowerCase().includes('done')) {
            icon = '✅'; // Finalizado correctamente
        }

        iconElement.text(icon);
    }

    $('#cancel-upload-btn').on('click', function () {
        if (currentUpload) {
            currentUpload.abort();
            $('#status-text').text('Subida cancelada');
            $('.progress-bar div').css('background', 'gray');
            $('#upload-percent').text('Cancelado');
            $(this).hide();
        }
    });

    setInterval(updateStatus, 2000);
    updateStatus(); // Carga inmediata al entrar/refrescar
});
