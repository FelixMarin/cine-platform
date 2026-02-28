// ui.js - Versión corregida

function showUploadSection() {
    $('#profile-card').fadeIn(300);
    $('#upload-card').fadeIn(300);
    // NO OCULTAR LA ESTIMACIÓN - $('#estimate-info').hide();  <-- ELIMINADO
    $('#video-preview-container').hide();
    $('#selected-file').text('Ningún archivo seleccionado');
    $('#video-input').val('');

    // Limpiar archivo seleccionado
    if (window.optimizerUpload) {
        window.optimizerUpload.selectedFile = null;
    }
}

function hideUploadSection() {
    $('#profile-card').hide();  // Forzar ocultación
    $('#upload-card').fadeOut(300);
    // NO tocar estimate-info
}

function showProgressSection() {
    $('#progressContainer').fadeIn(300);
    $('#cancel-process-container').fadeIn(300);
    $('#current-profile-badge').fadeIn(300);
}

function hideProgressSection() {
    $('#progressContainer').fadeOut(300);
    $('#cancel-process-container').fadeOut(300);
    $('#current-profile-badge').fadeOut(300);
}

function resetAfterCompletion(from) {

    // Actualizar estados globales si existen
    if (window.optimizerStatus) {
        if (typeof window.optimizerStatus.setProcessing === 'function') {
            window.optimizerStatus.setProcessing(false);
        }
        if (typeof window.optimizerStatus.setUserInitiated === 'function') {
            window.optimizerStatus.setUserInitiated(false);
        }
    }

    // Ocultar sección de progreso y mostrar sección de subida
    hideProgressSection();
    showUploadSection();

    // Resetear barras de progreso
    $('#progressBar').css('width', '0%').attr('aria-valuenow', 0);
    $('#progressText').text('0%');
    $('#upload-progress-bar').css('width', '0%').text('0%');
    $('#upload-status').hide();
    $('#cancel-upload-btn').hide();

    // Limpiar estadísticas
    $('#stat-frames, #stat-fps, #stat-time, #stat-bitrate, #stat-speed, #currentFile').text('–');

    // Limpiar información del video
    $('#info-name, #info-duration, #info-resolution, #info-format, #info-vcodec, #info-acodec, #info-size').text('–');

    // Resetear icono de estado
    $('#statusIcon').text('🟢');

    // Limpiar variable local (si existe en el ámbito global)
    if (window.optimizerUpload) {
        window.optimizerUpload.uploadedFilename = null;
    }
}

// Exportar
window.optimizerUI = {
    showUploadSection,
    hideUploadSection,
    showProgressSection,
    hideProgressSection,
    resetAfterCompletion
};