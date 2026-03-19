/**
 * Profile Page - Profile Modal
 * Gestión del modal de perfil de usuario
 */
(function() {
    'use strict';

    /**
     * Muestra el modal de perfil cargando los datos del usuario
     */
    window.showProfileModal = async function() {
        var modal = document.getElementById('profileModal');
        var overlay = document.getElementById('modalOverlay');
        var modalBody = document.getElementById('profileModalBody');
        
        if (!modal || !overlay || !modalBody) return;
        
        modal.style.display = 'block';
        overlay.style.display = 'block';
        modalBody.innerHTML = '<div class="loading-spinner">Cargando perfil...</div>';
        
        // Cerrar dropdown
        var menu = document.getElementById('profileMenu');
        if (menu) menu.classList.remove('show');
        
        try {
            var data = await window.fetchProfile();
            
            if (data.success) {
                window.setCurrentProfile(data.profile);
                window.renderProfileForm(data.profile);
            } else {
                modalBody.innerHTML = '<div class="error-message">Error: ' + window.escapeHtml(data.error) + '</div>';
            }
        } catch (error) {
            modalBody.innerHTML = '<div class="error-message">Error de conexión</div>';
            console.error('Error:', error);
        }
    };

    /**
     * Renderiza el formulario de perfil con los datos del usuario
     * @param {Object} profile - Datos del perfil
     */
    window.renderProfileForm = function(profile) {
        var modalBody = document.getElementById('profileModalBody');
        if (!modalBody) return;
        
        var defaultAvatar = window.PROFILE_CONFIG ? window.PROFILE_CONFIG.avatar.defaultAvatar : '/static/images/default.jpg';
        var timestamp = Date.now();
        var avatarUrl = (profile.avatar_url || defaultAvatar) + '?t=' + timestamp;
        
        modalBody.innerHTML = `
            <div class="profile-avatar-section">
                <img src="${avatarUrl}" 
                     alt="Avatar" 
                     class="profile-avatar-large"
                     id="profileAvatarPreview"
                     onerror="this.src='${defaultAvatar}'">
                <button class="btn-secondary btn-small" onclick="showAvatarModal()">
                    Cambiar avatar
                </button>
            </div>
            
            <form class="profile-form" onsubmit="saveProfile(event)">
                <div class="form-group">
                    <label>Nombre de usuario</label>
                    <input type="text" value="${window.escapeHtml(profile.username)}" readonly class="readonly-field">
                    <small class="field-note">No se puede modificar</small>
                </div>
                
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" value="${window.escapeHtml(profile.email)}" readonly class="readonly-field">
                    <small class="field-note">No se puede modificar</small>
                </div>
                
                <div class="form-group">
                    <label for="displayName">Nombre para mostrar</label>
                    <input type="text" 
                           id="displayName" 
                           name="display_name" 
                           value="${window.escapeHtml(profile.display_name || '')}" 
                           placeholder="Cómo quieres que te llamen">
                </div>
                
                <div class="form-group">
                    <label for="bio">Biografía</label>
                    <textarea id="bio" 
                              name="bio" 
                              rows="4" 
                              placeholder="Cuéntanos algo sobre ti...">${window.escapeHtml(profile.bio || '')}</textarea>
                </div>
                
                <div class="form-group">
                    <label for="privacyLevel">Privacidad</label>
                    <select id="privacyLevel" name="privacy_level">
                        <option value="public" ${profile.privacy_level === 'public' ? 'selected' : ''}>Público</option>
                        <option value="followers" ${profile.privacy_level === 'followers' ? 'selected' : ''}>Solo seguidores</option>
                        <option value="private" ${profile.privacy_level === 'private' ? 'selected' : ''}>Privado</option>
                    </select>
                </div>
                
                <div class="form-actions">
                    <button type="button" class="btn-secondary" onclick="closeProfileModal()">Cancelar</button>
                    <button type="submit" class="btn-primary">Guardar cambios</button>
                </div>
            </form>
        `;
    };

    /**
     * Guarda los cambios del perfil
     * @param {Event} event - Evento del formulario
     */
    window.saveProfile = async function(event) {
        event.preventDefault();
        
        var form = event.target;
        var formData = new FormData(form);
        var data = {
            display_name: formData.get('display_name'),
            bio: formData.get('bio'),
            privacy_level: formData.get('privacy_level')
        };
        
        try {
            var result = await window.updateProfile(data);
            
            if (result.success) {
                if (typeof window.showNotification === 'function') {
                    window.showNotification('Perfil actualizado', 'Los cambios se guardaron correctamente', 'success');
                }
                
                // Actualizar nombre en el header
                if (data.display_name) {
                    var profileNameEl = document.querySelector('.profile-name');
                    if (profileNameEl) profileNameEl.textContent = data.display_name;
                }
                
                window.closeProfileModal();
            } else {
                if (typeof window.showNotification === 'function') {
                    window.showNotification('Error', result.error || 'No se pudo guardar', 'error');
                }
            }
        } catch (error) {
            if (typeof window.showNotification === 'function') {
                window.showNotification('Error', 'No se pudo guardar el perfil', 'error');
            }
            console.error('Error:', error);
        }
    };

    /**
     * Cierra el modal de perfil
     */
    window.closeProfileModal = function() {
        var modal = document.getElementById('profileModal');
        var overlay = document.getElementById('modalOverlay');
        
        if (modal) modal.style.display = 'none';
        if (overlay) overlay.style.display = 'none';
    };

})();
