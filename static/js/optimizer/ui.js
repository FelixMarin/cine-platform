// ui.js - Funciones de UI (mostrar/ocultar contenedores)

function showUploadSection() {
    $('#profile-card').fadeIn();
    $('#upload-card').fadeIn();
    $('#estimate-info').hide();
    $('#video-preview-container').hide();
    $('#selected-file').text('Ningún archivo seleccionado');
    $('#video-input').val('');
    window.optimizerUpload.selectedFile = null;
}

function hideUploadSection() {
    $('#profile-card').fadeOut();
    $('#upload-card').fadeOut();
    $('#estimate-info').hide();
}

function showProgressSection() {
    $('#progressContainer').fadeIn();
    $('#cancel-process-container').fadeIn();
    $('#current-profile-badge').fadeIn();
}

function hideProgressSection() {
    $('#progressContainer').fadeOut();
    $('#cancel-process-container').fadeOut();
    $('#current-profile-badge').fadeOut();
}

function resetAfterCompletion() {
    window.optimizerStatus.setProcessing(false);
    window.optimizerStatus.setUserInitiated(false);

    hideProgressSection();
    showUploadSection();

    $('#progressBar').css('width', '0%');
    $('#progressText').text('0%');
    $('#upload-progress-bar').css('width', '0%').text('0%');
    $('#upload-status').hide();

    $('#stat-frames, #stat-fps, #stat-time, #stat-bitrate, #stat-speed').text('–');
    $('#info-name, #info-duration, #info-resolution, #info-format, #info-vcodec, #info-acodec, #info-size').text('–');
    $('#currentFile').text('Ninguno');
    $('#statusIcon').text('🟢');

    console.log('🔄 Interfaz reseteada completamente');
}

// Exportar
window.optimizerUI = {
    showUploadSection,
    hideUploadSection,
    showProgressSection,
    hideProgressSection,
    resetAfterCompletion
};