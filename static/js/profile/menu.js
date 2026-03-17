/**
 * Profile Page - Menu
 * Gestión del menú desplegable de perfil
 */
(function() {
    'use strict';

    /**
     * Toggle del menú desplegable de perfil
     */
    window.toggleProfileMenu = function() {
        var menu = document.getElementById('profileMenu');
        if (menu) {
            menu.classList.toggle('show');
        }
    };

    /**
     * Cerrar menú al hacer clic fuera
     */
    document.addEventListener('click', function(event) {
        var dropdown = document.getElementById('profileDropdown');
        var menu = document.getElementById('profileMenu');
        
        if (dropdown && menu && !dropdown.contains(event.target) && menu.classList.contains('show')) {
            menu.classList.remove('show');
        }
    });

})();
