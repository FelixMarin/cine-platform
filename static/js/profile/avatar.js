/**
 * Profile Page - Avatar
 * Gestión del avatar de usuario
 */
(function() {
    'use strict';

    /**
     * Muestra el modal de cambio de avatar
     */
    window.showAvatarModal = function() {
        var modalBody = document.querySelector('#profileModal .modal-body');
        if (!modalBody) return;
        
        var defaultAvatar = window.PROFILE_CONFIG ? window.PROFILE_CONFIG.avatar.defaultAvatar : '/static/images/default.jpg';
        var timestamp = Date.now();
        // Usar sessionStorage para obtener la última URL del avatar si está disponible
        var savedAvatar = sessionStorage.getItem('lastAvatarUrl') || window.getCurrentProfile()?.avatar_url || defaultAvatar;
        var avatarUrl = savedAvatar + (savedAvatar.includes('?') ? '&' : '?') + 't=' + timestamp;
        
        modalBody.innerHTML = `
            <div class="avatar-upload-container">
                <div class="current-avatar">
                    <img src="${avatarUrl}" 
                         alt="Avatar actual" 
                         id="currentAvatarPreview"
                         class="avatar-preview-large"
                         onerror="this.src='${defaultAvatar}'">
                </div>
                
                <div class="upload-controls">
                    <label for="avatarInput" class="btn-primary btn-upload">
                        <span class="upload-icon">📁</span>
                        Seleccionar imagen
                    </label>
                    <input type="file" 
                           id="avatarInput" 
                           accept="image/jpeg,image/png,image/gif" 
                           style="display: none;"
                           onchange="handleAvatarSelected(this)">
                    
                    <p class="upload-hint">
                        Formatos: JPG, PNG, GIF<br>
                        Tamaño máximo: 2MB
                    </p>
                </div>
                
                <div id="avatarPreviewContainer" style="display: none;">
                    <h4>Vista previa</h4>
                    <div class="preview-container">
                        <img id="avatarPreview" src="" alt="Vista previa">
                    </div>
                    <div class="preview-actions">
                        <button class="btn-secondary" onclick="cancelAvatarUpload()">Cancelar</button>
                        <button class="btn-primary" onclick="doUploadAvatar()" id="uploadBtn">
                            Subir avatar
                        </button>
                    </div>
                </div>
                
                <div id="uploadProgress" style="display: none;">
                    <div class="progress-bar-container">
                        <div class="progress-bar" id="uploadProgressBar" style="width: 0%"></div>
                    </div>
                    <span id="uploadStatus">Subiendo...</span>
                </div>
            </div>
        `;
    };

    /**
     * Maneja la selección de un archivo de avatar
     * @param {HTMLInputElement} input - Input de archivo
     */
    window.handleAvatarSelected = function(input) {
        if (!input.files || !input.files[0]) return;
        
        var file = input.files[0];
        var config = window.PROFILE_CONFIG ? window.PROFILE_CONFIG.avatar : { allowedTypes: ['image/jpeg', 'image/png', 'image/gif'], maxSize: 2 * 1024 * 1024 };
        
        if (!config.allowedTypes.includes(file.type)) {
            if (typeof window.showNotification === 'function') {
                window.showNotification('Error', 'Formato no válido. Usa JPG, PNG o GIF', 'error');
            }
            input.value = '';
            return;
        }
        
        if (file.size > config.maxSize) {
            if (typeof window.showNotification === 'function') {
                window.showNotification('Error', 'La imagen no puede superar los 2MB', 'error');
            }
            input.value = '';
            return;
        }
        
        var reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('avatarPreview').src = e.target.result;
            document.getElementById('avatarPreviewContainer').style.display = 'block';
            document.querySelector('.upload-controls').style.display = 'none';
        };
        reader.readAsDataURL(file);
        
        window.setSelectedAvatarFile(file);
    };

    /**
     * Cancela la subida de avatar
     */
    window.cancelAvatarUpload = function() {
        document.getElementById('avatarPreviewContainer').style.display = 'none';
        document.querySelector('.upload-controls').style.display = 'block';
        document.getElementById('avatarInput').value = '';
        window.setSelectedAvatarFile(null);
    };

    /**
     * Cierra el modal de avatar y vuelve al formulario de perfil
     */
    window.closeAvatarModal = function() {
        var profile = window.getCurrentProfile();
        if (profile) {
            window.renderProfileForm(profile);
        }
    };

    /**
     * Función para cargar los datos del perfil y mostrar el modal
     */
    window.loadProfileAndShowModal = async function() {
        try {
            var data = await window.fetchProfile();
            
            if (data.success) {
                window.setCurrentProfile(data.profile);
                window.renderProfileForm(data.profile);
            }
        } catch (error) {
            console.error('Error recargando perfil:', error);
        }
    };

    /**
     * Realiza la subida del avatar
     */
    window.doUploadAvatar = async function() {
        var file = window.getSelectedAvatarFile();
        if (!file) return;
        
        var uploadBtn = document.getElementById('uploadBtn');
        var progressContainer = document.getElementById('uploadProgress');
        var progressBar = document.getElementById('uploadProgressBar');
        var statusEl = document.getElementById('uploadStatus');
        
        uploadBtn.disabled = true;
        progressContainer.style.display = 'block';
        
        try {
            var result = await window.uploadAvatarApi(file);
            
            if (result.success) {
                progressBar.style.width = '100%';
                statusEl.textContent = '¡Completado!';
                
                var timestamp = Date.now();
                var avatarUrl = result.avatar_url + '?t=' + timestamp;
                
                // 1. Actualizar avatar en el menú lateral (buscar por id común)
                var menuAvatar = document.getElementById('avatar-img');
                if (menuAvatar) {
                    menuAvatar.src = avatarUrl;
                }
                
                // 2. Actualizar avatar en el modal de perfil
                var profileAvatarPreview = document.getElementById('profileAvatarPreview');
                if (profileAvatarPreview) {
                    profileAvatarPreview.src = avatarUrl;
                }
                
                // 3. Actualizar cualquier otra imagen de avatar en la página
                document.querySelectorAll('.profile-avatar, .avatar-preview-large, [class*="avatar"]').forEach(function(img) {
                    if (img.id !== 'avatar-img' && img.tagName === 'IMG') {
                        img.src = avatarUrl;
                    }
                });
                
                // 4. Guardar la nueva URL en sessionStorage para persistencia
                sessionStorage.setItem('lastAvatarUrl', avatarUrl);
                
                // 5. Actualizar el perfil local con el nuevo avatar
                var currentProfile = window.getCurrentProfile();
                if (currentProfile) {
                    currentProfile.avatar_url = result.avatar_url;
                }
                
                if (typeof window.showNotification === 'function') {
                    window.showNotification('Éxito', 'Avatar actualizado correctamente', 'success');
                }
                
                // Cerrar modal de avatar y recargar datos del perfil
                window.closeAvatarModal();
                
                // Recargar datos del perfil y mostrar modal
                setTimeout(async function() {
                    await window.loadProfileAndShowModal();
                }, 300);
            } else {
                throw new Error(result.error || 'Error al subir avatar');
            }
        } catch (error) {
            progressContainer.style.display = 'none';
            if (typeof window.showNotification === 'function') {
                window.showNotification('Error', error.message, 'error');
            }
            uploadBtn.disabled = false;
        }
    };

    // Alias para compatibilidad - la función original se llamaba uploadAvatar pero ya existe en api.js
    // Por eso usamos doUploadAvatar y exponemos uploadAvatar como alias
    window.uploadAvatar = async function() {
        await window.doUploadAvatar();
    };

})();
