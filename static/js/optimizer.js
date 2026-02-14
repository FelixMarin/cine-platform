$(document).ready(function () {
    let currentUpload = null;

    // ============================
    //  MENÚ LATERAL
    // ============================
    window.toggleMenu = function () {
        const $menu = $('#sideMenu');
        const $overlay = $('.menu-overlay');
        $menu.toggleClass('open');
        $overlay.toggleClass('active');
    };

    window.toggleCollapse = function () {
        const $menu = $('#sideMenu');
        const $mainContent = $('#mainContent');
        const $collapseBtn = $('.menu-collapse-btn');

        $menu.toggleClass('collapsed');
        $mainContent.toggleClass('expanded');

        if ($menu.hasClass('collapsed')) {
            $collapseBtn.html('▶').attr('title', 'Expandir menú');
        } else {
            $collapseBtn.html('◀').attr('title', 'Colapsar menú');
        }

        try {
            localStorage.setItem('menuCollapsed', $menu.hasClass('collapsed'));
        } catch (e) { }
    };

    window.showTab = function (tabName) {
        window.location.href = '/?tab=' + tabName;
    };

    // ============================
    //  SUBIDA DE ARCHIVOS
    // ============================

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

    $('#cancel-upload-btn').on('click', function () {
        if (currentUpload) {
            currentUpload.abort();
            $('#status-text').text('Subida cancelada');
            $('.progress-bar div').css('background', 'gray');
            $('#upload-percent').text('Cancelado');
            $(this).hide();
        }
    });

    // ============================
    //  BARRA DE PROGRESO NUEVA
    // ============================

    function updateProgress(step) {
        const $bar = $('#progressBar');
        const $text = $('#progressText');
        const $wrap = $('#progressContainer');

        if (!step || step === 0) {
            $wrap.hide();
            $text.hide();
            $bar.css('width', '0%');
            return;
        }

        // Mostrar barra al iniciar
        $wrap.show();
        $text.show();

        if (step === 1) {
            $bar.css('width', '50%');
            $text.text('Procesando vídeo (optimización completa)…');
        }

        if (step === 2) {
            $bar.css('width', '100%');
            $text.text('Validando duración…');
        }
    }

    // ============================
    //  HISTORIAL
    // ============================

    function updateHistory(history) {
        $('#history').empty();
        history.forEach(item => {
            const name = item.name;
            const status = item.status;
            const timestamp = item.timestamp || '–';
            const duration = item.duration || '–';

            const statusClass = status.toLowerCase().includes('error')
                ? 'status-error'
                : 'status-success';

            $('#history').append(`
                <tr>
                    <td>${name}</td>
                    <td class="${statusClass}">${status}</td>
                    <td>${timestamp}</td>
                    <td>${duration}</td>
                </tr>
            `);
        });
    }

    // ============================
    //  ICONO DE ESTADO
    // ============================

    function updateStatusIcon(logLine) {
        const $icon = $('#statusIcon');
        const line = logLine || '';

        let icon = '🟡';

        if (line.toLowerCase().includes('error')) icon = '🔴';
        else if (line.toLowerCase().includes('frame') || line.toLowerCase().includes('speed')) icon = '🟢';
        else if (line.toLowerCase().includes('completed')) icon = '✅';

        $icon.text(icon);
    }

    // ============================
    //  POLLING /status
    // ============================

    function formatSecondsToHHMMSS(seconds) {
        seconds = parseInt(seconds, 10);
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return [h, m, s].map(v => String(v).padStart(2, '0')).join(':');
    }

    function updateStatus() {
        $.getJSON('/status', function (data) {
            $('#currentFile').text(data.current_video || 'Ninguno');

            // Log-line → tabla de progreso
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
            $('#stat-time').text(campos['time'] ? campos['time'].split('.')[0] : '–');
            $('#stat-bitrate').text(campos['bitrate'] || '–');
            $('#stat-speed').text(campos['speed'] || '–');

            // Info del vídeo
            const info = data.video_info || {};
            const durSeg = info.duration ? info.duration.split(' ')[0] : null;
            $('#info-duration').text(durSeg ? formatSecondsToHHMMSS(durSeg) : '–');
            $('#info-name').text(info.name || '–');
            $('#info-resolution').text(info.resolution || '–');
            $('#info-format').text(info.format || '–');
            $('#info-vcodec').text(info.vcodec || '–');
            $('#info-acodec').text(info.acodec || '–');
            $('#info-size').text(info.size || '–');

            // NUEVO: barra de progreso
            updateProgress(data.current_step);

            // Historial
            updateHistory(data.history);

            // Icono
            updateStatusIcon(data.log_line);
        });
    }

    // ============================
    //  INICIALIZACIÓN
    // ============================

    const savedState = localStorage.getItem('menuCollapsed');
    const $menu = $('#sideMenu');
    const $mainContent = $('#mainContent');
    const $collapseBtn = $('.menu-collapse-btn');

    if (savedState === 'true' && $(window).width() > 768) {
        $menu.addClass('collapsed');
        $mainContent.addClass('expanded');
        $collapseBtn.html('▶');
    }

    $('.menu-item, .menu-logout').on('click', function () {
        if ($(window).width() <= 768) toggleMenu();
    });

    setInterval(updateStatus, 2000);
    updateStatus();
});
