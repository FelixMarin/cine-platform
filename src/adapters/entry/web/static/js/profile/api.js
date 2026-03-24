/**
 * Profile Page - API
 * Llamadas fetch para la API de perfil
 */
(function() {
    'use strict';

    /**
     * Obtiene los datos del perfil del usuario actual
     */
    window.fetchProfile = async function() {
        var endpoint = window.PROFILE_CONFIG ? window.PROFILE_CONFIG.endpoints.getProfile : '/api/profile/me';
        var response = await fetch(endpoint);
        return await response.json();
    };

    /**
     * Actualiza los datos del perfil del usuario
     * @param {Object} data - Datos a actualizar {display_name, bio, privacy_level}
     */
    window.updateProfile = async function(data) {
        var endpoint = window.PROFILE_CONFIG ? window.PROFILE_CONFIG.endpoints.updateProfile : '/api/profile/update';
        var response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        return await response.json();
    };

    /**
     * Sube un nuevo avatar para el usuario (llamada API interna)
     * @param {File} file - Archivo de imagen
     */
    window.uploadAvatarApi = async function(file) {
        var endpoint = window.PROFILE_CONFIG ? window.PROFILE_CONFIG.endpoints.uploadAvatar : '/api/profile/avatar';
        var formData = new FormData();
        formData.append('avatar', file);
        
        var response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });
        return await response.json();
    };

})();
