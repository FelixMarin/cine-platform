// upload.js - Manejo de subida de archivos

let currentUpload = null;
let selectedFile = null;
let isUploading = false;

function estimateSize(file) {
    if (!file) return;

    // Tamaño del archivo en MB
    const fileSizeMB = file.size / (1024 * 1024);

    // Ratios según perfil (deben coincidir con los del servidor)
    const ratios = {
        'ultra_fast': 0.15,   // 15% del original
        'fast': 0.12,         // 12% del original
        'balanced': 0.10,     // 10% del original
        'high_quality': 0.25, // 25% del original
        'master': 0.50        // 50% del original
    };

    const profile = window.optimizerProfiles.currentProfile;
    const ratio = ratios[profile] || 0.10;
    const estimatedMB = fileSizeMB * ratio;

    // Calcular porcentaje de compresión REAL
    // Si el ratio es 0.10 (10%), la compresión es 90%
    // Si el ratio es 0.15 (15%), la compresión es 85%
    // Si el ratio es 0.25 (25%), la compresión es 75%
    // Si el ratio es 0.50 (50%), la compresión es 50%
    const compressionPercent = Math.round((1 - ratio) * 100);

    // Actualizar UI
    $('#estimate-info').show();
    $('#estimate-original').text(fileSizeMB.toFixed(1) + ' MB');
    $('#estimate-final').text(estimatedMB.toFixed(1) + ' MB');
    $('#estimate-ratio').text(compressionPercent + '%');
}

function setupUploadHandlers() {

    $('#video-input').on('change', function () {
        if (isUploading) {
            alert('Hay una subida en curso. Espera a que termine o cancélala.');
            this.value = '';
            return;
        }

        const file = this.files[0];
        if (file) {
            selectedFile = file;
            $('#selected-file').text(file.name);

            const preview = $('#video-preview')[0];
            if (preview.src && preview.src.startsWith('blob:')) {
                URL.revokeObjectURL(preview.src);
            }

            const url = URL.createObjectURL(file);
            $('#video-preview').attr('src', url);
            $('#video-preview-container').fadeIn(300);
            estimateSize(file);
        } else {
            selectedFile = null;
            $('#selected-file').text('Ningún archivo seleccionado');
            $('#video-preview').attr('src', '');
            $('#video-preview-container').fadeOut(300);
            $('#estimate-info').hide();
        }
    });

    $('#upload-btn').on('click', handleUpload);
    $('#cancel-upload-btn').on('click', cancelUpload);
}

function handleUpload(e) {
    e.preventDefault();
    e.stopPropagation();

    const fileInput = $('#video-input')[0];
    if (!fileInput.files.length) {
        alert('Selecciona un archivo primero.');
        return;
    }

    if (isUploading) {
        alert('Ya hay una subida en curso');
        return;
    }

    const file = fileInput.files[0];

    // Marcar que estamos subiendo
    isUploading = true;

    // 1. OCULTAR CONTENEDOR DE PERFIL DE OPTIMIZACIÓN
    $('#profile-card').fadeOut(300);

    // 2. MOSTRAR ESTIMACIÓN DE TAMAÑO (ya debería estar visible, pero aseguramos)
    $('#estimate-info').show();

    // 3. DESHABILITAR BOTÓN SUBIR
    $('#upload-btn').prop('disabled', true).css('opacity', '0.5');

    // 4. DESHABILITAR LABEL DEL INPUT FILE (en lugar del input oculto)
    $('label[for="video-input"]').addClass('disabled-label').css({
        'opacity': '0.5',
        'pointer-events': 'none',
        'cursor': 'not-allowed'
    });

    // Limpiar datos anteriores
    $('#info-name, #info-duration, #info-resolution, #info-format, #info-vcodec, #info-acodec, #info-size').text('–');
    $('#currentFile').text('Ninguno');

    window.optimizerStatus.setUserInitiated(true);
    window.optimizerStatus.setProcessing(true);

    const profileNames = {
        'ultra_fast': 'Ultra Rápido',
        'fast': 'Rápido',
        'balanced': 'Balanceado',
        'high_quality': 'Alta Calidad',
        'master': 'Master'
    };

    $('#processing-profile').text(profileNames[window.optimizerProfiles.currentProfile] || window.optimizerProfiles.currentProfile);
    $('#current-profile-badge').fadeIn(300);

    // MOSTRAR BARRA DE PROGRESO Y BOTÓN CANCELAR
    $('#upload-status').css('display', 'block').fadeIn(300);
    $('#cancel-upload-btn').show();
    $('#status-text').text('Subiendo archivo...');
    $('#upload-progress-bar').css('width', '0%').text('0%');
    $('#upload-percent').text('0%');

    const formData = new FormData();
    formData.append('video', file);
    formData.append('profile', window.optimizerProfiles.currentProfile);

    // Usar XMLHttpRequest directamente para mejor control
    const xhr = new XMLHttpRequest();
    currentUpload = xhr;

    // Variable para controlar si ya se manejó la respuesta
    let handled = false;

    // Configurar progreso
    xhr.upload.addEventListener('progress', function (evt) {
        if (evt.lengthComputable) {
            const percent = Math.round((evt.loaded / evt.total) * 100);

            // Asegurar que la barra de progreso y botón cancelar estén visibles
            $('#upload-status').show();
            $('#cancel-upload-btn').show();
            $('#upload-progress-bar').css('width', percent + '%').text(percent + '%');
            $('#upload-percent').text(percent + '%');
        }
    });

    // Configurar carga completa
    xhr.addEventListener('load', function () {
        if (handled) return;
        handled = true;

        if (xhr.status === 202 || xhr.status === 200) {
            try {
                const resp = JSON.parse(xhr.responseText);

                $('#status-text').text('Subida completada. Iniciando optimización...');
                $('#cancel-upload-btn').hide();

                // IMPORTANTE: Asegurar que el perfil está oculto
                $('#profile-card').hide();  // <-- FORZAR OCULTACIÓN

                // Ocultar barra de subida y mostrar barra de progreso
                $('#upload-status').fadeOut(300, function () {
                    // Después de ocultar la subida, mostrar el progreso
                    window.optimizerUI.hideUploadSection();  // <-- ESTO OCULTA upload-card pero NO muestra profile-card
                    window.optimizerUI.showProgressSection();
                    window.optimizerProgress.startMonitoring();
                });

            } catch (e) {
                console.error('❌ Error parseando respuesta:', e);
                handleError('Error parsing response');
            }
        } else {
            console.error('❌ Error en subida. Status:', xhr.status);
            let errorMsg = 'Error en la subida';
            try {
                const resp = JSON.parse(xhr.responseText);
                if (resp.error) errorMsg += ': ' + resp.error;
            } catch (e) { }
            handleError(errorMsg);
        }
    });

    // Configurar error de red
    xhr.addEventListener('error', function () {
        if (handled) return;
        handled = true;
        console.error('❌ Error de red en la subida');
        handleError('Error de red');
    });

    // Configurar timeout
    xhr.addEventListener('timeout', function () {
        if (handled) return;
        handled = true;
        console.error('❌ Timeout en la subida');
        handleError('Timeout - la subida tomó demasiado tiempo');
    });

    // Función para manejar errores
    function handleError(message) {
        $('#status-text').text(message);

        // REHABILITAR BOTONES Y MOSTRAR PERFIL
        $('#profile-card').fadeIn(300);
        $('#upload-btn').prop('disabled', false).css('opacity', '1');
        $('#video-input').prop('disabled', false);
        $('#cancel-upload-btn').hide();
        isUploading = false;

        window.optimizerUI.resetAfterCompletion('Error en subida');
    }

    // Abrir y enviar
    xhr.open('POST', '/process-file', true);
    xhr.withCredentials = true;
    const timeoutMs = (file.size / (1024 * 1024 * 1024)) * 60000 + 300000;
    xhr.timeout = Math.min(timeoutMs, 7200000);
    xhr.send(formData);
}

function cancelUpload() {
    if (currentUpload && isUploading) {
        currentUpload.abort();

        $('#status-text').text('Subida cancelada');
        $('#upload-progress-bar').css('background', 'gray').text('Cancelado');
        $('#upload-percent').text('Cancelado');

        // REHABILITAR BOTONES Y MOSTRAR PERFIL
        $('#profile-card').fadeIn(300);
        $('#upload-btn').prop('disabled', false).css('opacity', '1');
        $('#video-input').prop('disabled', false);
        $('#cancel-upload-btn').hide();
        isUploading = false;

        window.optimizerProgress.stopMonitoring();
        window.optimizerUI.resetAfterCompletion('Cancelado por usuario');
    }
}

// Exportar
window.optimizerUpload = {
    selectedFile: selectedFile,
    estimateSize: estimateSize,
    setupUploadHandlers: setupUploadHandlers,
    cancelUpload: cancelUpload,
    isUploading: () => isUploading
};