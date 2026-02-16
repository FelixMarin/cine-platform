$(document).ready(function () {
    let currentUpload = null;
    let currentProfile = 'balanced';
    let selectedFile = null;

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
    //  PERFILES DE OPTIMIZACIÓN
    // ============================
    function loadProfiles() {
        console.log('📥 Cargando perfiles...');

        $.ajax({
            url: '/optimizer/profiles',
            method: 'GET',
            success: function (profiles) {
                console.log('✅ Perfiles cargados:', profiles);
                renderProfiles(profiles);

                // Seleccionar perfil balanced por defecto
                setTimeout(() => {
                    selectProfile('balanced');
                }, 100);
            },
            error: function (xhr, status, error) {
                console.error('❌ Error cargando perfiles:', error);
                $('#profile-container').html(`
                    <div class="col-12">
                        <div class="alert alert-danger">
                            Error cargando perfiles. Por favor, recarga la página.
                        </div>
                    </div>
                `);
            }
        });
    }

    function renderProfiles(profiles) {
        const $container = $('#profile-container');
        $container.empty();

        const profileIcons = {
            'ultra_fast': '⚡',
            'fast': '🚀',
            'balanced': '⚖️',
            'high_quality': '🎯',
            'master': '💎'
        };

        const profileColors = {
            'ultra_fast': '#28a745',
            'fast': '#17a2b8',
            'balanced': '#ffc107',
            'high_quality': '#fd7e14',
            'master': '#dc3545'
        };

        const profileNames = {
            'ultra_fast': 'Ultra Rápido',
            'fast': 'Rápido',
            'balanced': 'Balanceado',
            'high_quality': 'Alta Calidad',
            'master': 'Master'
        };

        Object.entries(profiles).forEach(([key, profile]) => {
            const icon = profileIcons[key] || '🎬';
            const color = profileColors[key] || '#6c757d';
            const name = profileNames[key] || key;
            const description = profile.description || '';
            const preset = profile.preset || 'medium';
            const crf = profile.crf || 23;
            const resolution = profile.resolution || 'Auto';

            const col = $('<div>').addClass('col-md-4 col-sm-6 mb-3');

            const card = $(`
                <div class="profile-card" data-profile="${key}">
                    <div class="profile-icon" style="color: ${color}">${icon}</div>
                    <div class="profile-title">${name}</div>
                    <div class="profile-description">${description}</div>
                    <div>
                        <span class="profile-badge badge-speed">${preset}</span>
                        <span class="profile-badge badge-quality">CRF ${crf}</span>
                        <span class="profile-badge badge-size">${resolution}</span>
                    </div>
                </div>
            `);

            card.on('click', function () {
                selectProfile(key);
            });

            col.append(card);
            $container.append(col);
        });
    }

    window.selectProfile = function (profile) {
        console.log('📌 Perfil seleccionado:', profile);

        $('.profile-card').removeClass('selected');
        $(`.profile-card[data-profile="${profile}"]`).addClass('selected');

        currentProfile = profile;

        // Si hay un archivo seleccionado, estimar tamaño
        if (selectedFile) {
            estimateSize(selectedFile);
        }
    };

    // ============================
    //  ESTIMACIÓN DE TAMAÑO
    // ============================
    function estimateSize(file) {
        if (!file) return;

        $.ajax({
            url: '/optimizer/estimate',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                filepath: file.name,
                profile: currentProfile
            }),
            success: function (estimate) {
                console.log('📊 Estimación:', estimate);

                $('#estimate-info').addClass('show');
                $('#estimate-original').text(estimate.original_mb ?
                    estimate.original_mb.toFixed(1) + ' MB' : '?');
                $('#estimate-final').text(estimate.estimated_mb ?
                    estimate.estimated_mb.toFixed(1) + ' MB' : '?');
                $('#estimate-ratio').text(estimate.compression_ratio || '?');
            },
            error: function (xhr) {
                console.error('❌ Error estimando:', xhr.responseJSON);
            }
        });
    }

    // ============================
    //  SUBIDA DE ARCHIVOS
    // ============================
    $('#video-input').on('change', function () {
        const file = this.files[0];
        if (file) {
            selectedFile = file;
            $('#selected-file').text(file.name);

            const url = URL.createObjectURL(file);
            $('#video-preview').attr('src', url);
            $('#video-preview-container').fadeIn();

            // Estimar tamaño
            estimateSize(file);

            $('#video-preview').on('loadedmetadata', function () {
                URL.revokeObjectURL(url);
            });
        } else {
            selectedFile = null;
            $('#selected-file').text('Ningún archivo seleccionado');
            $('#video-preview-container').fadeOut();
            $('#estimate-info').removeClass('show');
        }
    });

    $('#upload-form').on('submit', function (e) {
        e.preventDefault();
        const fileInput = $('#video-input')[0];
        if (!fileInput.files.length) {
            alert('Selecciona un archivo primero.');
            return;
        }

        // Mostrar perfil seleccionado en progreso
        const profileNames = {
            'ultra_fast': 'Ultra Rápido',
            'fast': 'Rápido',
            'balanced': 'Balanceado',
            'high_quality': 'Alta Calidad',
            'master': 'Master'
        };

        $('#processing-profile').text(profileNames[currentProfile] || currentProfile);
        $('#current-profile-badge').fadeIn();

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
                    $('#selected-file').text('Ningún archivo seleccionado');
                    selectedFile = null;
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
    //  BARRA DE PROGRESO
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

        if (!history || history.length === 0) {
            $('#history').append(`
                <tr>
                    <td colspan="6" class="text-center text-muted">
                        No hay historial de procesamiento
                    </td>
                </tr>
            `);
            return;
        }

        history.forEach(item => {
            const name = item.name || 'Desconocido';
            const status = item.status || '–';
            const timestamp = item.timestamp || '–';
            const duration = item.duration || '–';
            const profile = item.profile || '–';
            const size = item.size || '–';

            const statusClass = status.toLowerCase().includes('error')
                ? 'status-error'
                : 'status-success';

            $('#history').append(`
                <tr>
                    <td>${name}</td>
                    <td><span class="badge badge-info">${profile}</span></td>
                    <td class="${statusClass}">${status}</td>
                    <td>${timestamp}</td>
                    <td>${duration}</td>
                    <td>${size}</td>
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

        let icon = '⚠️';

        if (line.toLowerCase().includes('error')) icon = '❌';
        else if (line.toLowerCase().includes('frame') || line.toLowerCase().includes('speed')) icon = '✅';
        else if (line.toLowerCase().includes('completed')) icon = '✅';

        $icon.text(icon);
    }

    // ============================
    //  POLLING /status
    // ============================
    function formatSecondsToHHMMSS(seconds) {
        seconds = parseInt(seconds, 10);
        if (isNaN(seconds)) return '–';

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

            // Barra de progreso
            updateProgress(data.current_step);

            // Historial
            updateHistory(data.history);

            // Icono
            updateStatusIcon(data.log_line);

            // Ocultar badge de perfil cuando no hay proceso
            if (!data.current_video) {
                $('#current-profile-badge').fadeOut();
            }
        }).fail(function () {
            console.log('Error conectando con el servidor');
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

    // Cargar perfiles al iniciar
    loadProfiles();

    // Iniciar polling de estado
    setInterval(updateStatus, 2000);
    updateStatus();
});