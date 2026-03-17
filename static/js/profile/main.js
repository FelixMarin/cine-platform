/**
 * Profile Page - Main
 * Inicialización y puntos de entrada
 */
(function() {
    'use strict';

    // Variables para controlar la inicialización
    var dependenciesReady = false;
    var initAttempts = 0;
    var MAX_ATTEMPTS = 20; // 2 segundos máximo (20 * 100ms)

    /**
     * Función de inicialización
     */
    function init() {
        console.log('[Profile] Inicializando página de perfil');

        // Los event listeners del menú ya están configurados en menu.js
        // No hay más inicialización necesaria para profile.js
        
        console.log('[Profile] Inicialización completada');
    }

    /**
     * Verifica las dependencias antes de inicializar
     */
    function checkDependenciesAndInit() {
        initAttempts++;

        // Verificar que todas las dependencias necesarias existen
        var missing = [];
        
        if (!window.PROFILE_CONFIG) missing.push('PROFILE_CONFIG');
        if (!window.profileState) missing.push('profileState');
        if (!window.escapeHtml) missing.push('escapeHtml');
        if (!window.closeAllModals) missing.push('closeAllModals');
        if (!window.fetchProfile) missing.push('fetchProfile');
        if (!window.updateProfile) missing.push('updateProfile');
        if (!window.uploadAvatar) missing.push('uploadAvatar');
        if (!window.uploadAvatarApi) missing.push('uploadAvatarApi');
        if (!window.toggleProfileMenu) missing.push('toggleProfileMenu');
        if (!window.showProfileModal) missing.push('showProfileModal');
        if (!window.renderProfileForm) missing.push('renderProfileForm');
        if (!window.saveProfile) missing.push('saveProfile');
        if (!window.closeProfileModal) missing.push('closeProfileModal');
        if (!window.showAvatarModal) missing.push('showAvatarModal');
        if (!window.handleAvatarSelected) missing.push('handleAvatarSelected');
        if (!window.cancelAvatarUpload) missing.push('cancelAvatarUpload');
        if (!window.doUploadAvatar) missing.push('doUploadAvatar');
        if (!window.closeAvatarModal) missing.push('closeAvatarModal');
        if (!window.loadProfileAndShowModal) missing.push('loadProfileAndShowModal');
        if (!window.showSettingsModal) missing.push('showSettingsModal');
        if (!window.closeSettingsModal) missing.push('closeSettingsModal');
        if (!window.showWatchlistModal) missing.push('showWatchlistModal');
        if (!window.closeWatchlistModal) missing.push('closeWatchlistModal');
        if (!window.getCurrentProfile) missing.push('getCurrentProfile');
        if (!window.setCurrentProfile) missing.push('setCurrentProfile');
        if (!window.getSelectedAvatarFile) missing.push('getSelectedAvatarFile');
        if (!window.setSelectedAvatarFile) missing.push('setSelectedAvatarFile');

        if (missing.length === 0) {
            console.log('[Profile] Todas las dependencias están listas, inicializando...');
            dependenciesReady = true;
            init();
        } else if (initAttempts < MAX_ATTEMPTS) {
            console.log('[Profile] Esperando dependencias: ' + missing.join(', ') + ' (intento ' + initAttempts + '/' + MAX_ATTEMPTS + ')');
            setTimeout(checkDependenciesAndInit, 100);
        } else {
            console.error('[Profile] Tiempo de espera agotado para dependencias:', missing);
            // Intentar inicializar de todos modos para no dejar la página sin funcionar
            console.warn('[Profile] Intentando inicializar sin todas las dependencias...');
            init();
        }
    }

    // Escuchar el evento de módulos cargados (disparado por el archivo principal)
    document.addEventListener('profile-modules-loaded', function() {
        console.log('[Profile] Evento profile-modules-loaded recibido');
        checkDependenciesAndInit();
    });

    // También intentar inmediatamente si los módulos ya están cargados
    setTimeout(checkDependenciesAndInit, 100);

})();
