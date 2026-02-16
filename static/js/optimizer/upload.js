// upload.js - Manejo de subida de archivos

let currentUpload = null;
let selectedFile = null;

function estimateSize(file) {
    if (!file) return;

    $.ajax({
        url: '/optimizer/estimate',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            filepath: file.name,
            profile: window.optimizerProfiles.currentProfile
        }),
        success: function (estimate) {
            console.log('📊 Estimación:', estimate);
            $('#estimate-info').show();
            $('#estimate-original').text(estimate.original_mb?.toFixed(1) + ' MB' || '?');
            $('#estimate-final').text(estimate.estimated_mb?.toFixed(1) + ' MB' || '?');
            $('#estimate-ratio').text(estimate.compression_ratio || '?');
        },
        error: (xhr) => console.error('❌ Error estimando:', xhr.responseJSON)
    });
}

function setupUploadHandlers() {
    $('#video-input').on('change', function () {
        const file = this.files[0];
        if (file) {
            selectedFile = file;
            $('#selected-file').text(file.name);

            const preview = $('#video-preview')[0];
            if (preview.src?.startsWith('blob:')) {
                URL.revokeObjectURL(preview.src);
            }

            const url = URL.createObjectURL(file);
            $('#video-preview').attr('src', url);
            $('#video-preview-container').fadeIn();
            estimateSize(file);
        } else {
            selectedFile = null;
            $('#selected-file').text('Ningún archivo seleccionado');
            $('#video-preview').attr('src', '');
            $('#video-preview-container').fadeOut();
            $('#estimate-info').hide();
        }
    });

    $('#upload-form').on('submit', handleUpload);
    $('#cancel-upload-btn').on('click', cancelUpload);
}

function handleUpload(e) {
    e.preventDefault();
    const fileInput = $('#video-input')[0];
    if (!fileInput.files.length) {
        alert('Selecciona un archivo primero.');
        return;
    }

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
    $('#current-profile-badge').fadeIn();

    $('#upload-status').fadeIn();
    $('#cancel-upload-btn').show();
    $('#status-text').text('Subiendo archivo...');
    $('#upload-progress-bar').css('width', '0%').text('0%');
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
                        $('#upload-progress-bar').css('width', percent + '%').text(percent + '%');
                        $('#upload-percent').text(percent + '%');
                    }
                });
            }
            return xhr;
        },
        success: function (resp) {
            $('#status-text').text('Subida completada. Iniciando optimización...');
            $('#cancel-upload-btn').hide();

            window.optimizerUI.hideUploadSection();
            window.optimizerUI.showProgressSection();
            window.optimizerProgress.startMonitoring();

            setTimeout(() => $('#upload-status').fadeOut(), 2000);
        },
        error: function (xhr) {
            $('#status-text').text('Error en la subida');
            $('#cancel-upload-btn').show();
            console.error(xhr.responseJSON?.error || "Error desconocido");
            window.optimizerUI.resetAfterCompletion();
        }
    });
}

function cancelUpload() {
    if (currentUpload) {
        currentUpload.abort();
        $('#status-text').text('Subida cancelada');
        $('#upload-progress-bar').css('background', 'gray').text('Cancelado');
        $('#upload-percent').text('Cancelado');
        $(this).hide();
        window.optimizerProgress.stopMonitoring();
        window.optimizerUI.resetAfterCompletion();
    }
}

// Exportar
window.optimizerUpload = {
    selectedFile,
    estimateSize,
    setupUploadHandlers,
    cancelUpload
};