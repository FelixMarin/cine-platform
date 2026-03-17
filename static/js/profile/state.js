/**
 * Profile Page - State Management
 * Estado global y getters/setters
 */
(function() {
    'use strict';

    // Estado global del perfil
    window.profileState = {
        currentProfile: null,
        selectedAvatarFile: null
    };

    // Getter para obtener el perfil actual
    window.getCurrentProfile = function() {
        return window.profileState.currentProfile;
    };

    // Setter para establecer el perfil actual
    window.setCurrentProfile = function(profile) {
        window.profileState.currentProfile = profile;
    };

    // Getter para el archivo de avatar seleccionado
    window.getSelectedAvatarFile = function() {
        return window.profileState.selectedAvatarFile;
    };

    // Setter para el archivo de avatar seleccionado
    window.setSelectedAvatarFile = function(file) {
        window.profileState.selectedAvatarFile = file;
    };

})();
