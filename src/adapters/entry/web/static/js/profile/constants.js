/**
 * Profile Page - Constants and Configuration
 * Constantes de configuración para el perfil de usuario
 */
(function() {
    'use strict';

    // Configuración de endpoints de API
    window.PROFILE_CONFIG = {
        endpoints: {
            getProfile: '/api/profile/me',
            updateProfile: '/api/profile/update',
            uploadAvatar: '/api/profile/avatar'
        },
        avatar: {
            maxSize: 2 * 1024 * 1024, // 2MB
            allowedTypes: ['image/jpeg', 'image/png', 'image/gif'],
            defaultAvatar: '/static/images/default.jpg'
        }
    };

})();
