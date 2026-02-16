// main.js - Punto de entrada principal

$(document).ready(function () {
    // Cargar estado del menú
    const savedState = localStorage.getItem('menuCollapsed');
    if (savedState === 'true' && $(window).width() > 768) {
        $('#sideMenu').addClass('collapsed');
        $('#mainContent').addClass('expanded');
        $('.menu-collapse-btn').html('▶');
    }

    // Eventos del menú
    $('.menu-item, .menu-logout').on('click', function () {
        if ($(window).width() <= 768) window.optimizerMenu.toggleMenu();
    });

    // Botón de cancelar proceso
    $('#cancel-process-btn').on('click', function () {
        if (confirm('¿Estás seguro de que quieres cancelar el proceso?')) {
            $.ajax({
                url: '/cancel-process',
                method: 'POST',
                success: function () {
                    console.log('✅ Proceso cancelado');
                    window.optimizerProgress.stopMonitoring();
                    window.optimizerUI.resetAfterCompletion();
                },
                error: function (xhr) {
                    console.error('❌ Error cancelando:', xhr.responseJSON);
                    alert('Error al cancelar el proceso: ' + (xhr.responseJSON?.error || 'Error desconocido'));
                }
            });
        }
    });

    // Inicialización
    window.optimizerUI.hideProgressSection();
    window.optimizerProfiles.loadProfiles();
    window.optimizerUpload.setupUploadHandlers();

    // Polling de estado
    setInterval(window.optimizerStatus.updateStatus, 2000);
    window.optimizerStatus.updateStatus();
});

// Exponer funciones del menú al ámbito global (para onclick en HTML)
window.toggleMenu = window.optimizerMenu.toggleMenu;
window.toggleCollapse = window.optimizerMenu.toggleCollapse;
window.showTab = window.optimizerMenu.showTab;
window.selectProfile = window.optimizerProfiles.selectProfile;