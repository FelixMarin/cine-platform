// ============================================
// PERFIL DE USUARIO - Menú y modales
// ============================================

let currentProfile = null;

// Toggle del menú desplegable
function toggleProfileMenu() {
    const menu = document.getElementById('profileMenu');
    if (menu) {
        menu.classList.toggle('show');
    }
}

// Cerrar menú al hacer clic fuera
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('profileDropdown');
    const menu = document.getElementById('profileMenu');
    
    if (dropdown && menu && !dropdown.contains(event.target) && menu.classList.contains('show')) {
        menu.classList.remove('show');
    }
});

// Cerrar todos los modales
function closeAllModals() {
    const profileModal = document.getElementById('profileModal');
    const settingsModal = document.getElementById('settingsModal');
    const watchlistModal = document.getElementById('watchlistModal');
    const modalOverlay = document.getElementById('modalOverlay');
    
    if (profileModal) profileModal.style.display = 'none';
    if (settingsModal) settingsModal.style.display = 'none';
    if (watchlistModal) watchlistModal.style.display = 'none';
    if (modalOverlay) modalOverlay.style.display = 'none';
}

// ============================================
// MODAL DE PERFIL
// ============================================

async function showProfileModal() {
    const modal = document.getElementById('profileModal');
    const overlay = document.getElementById('modalOverlay');
    const modalBody = document.getElementById('profileModalBody');
    
    if (!modal || !overlay || !modalBody) return;
    
    modal.style.display = 'block';
    overlay.style.display = 'block';
    modalBody.innerHTML = '<div class="loading-spinner">Cargando perfil...</div>';
    
    // Cerrar dropdown
    const menu = document.getElementById('profileMenu');
    if (menu) menu.classList.remove('show');
    
    try {
        const response = await fetch('/api/profile/me');
        const data = await response.json();
        
        if (data.success) {
            currentProfile = data.profile;
            renderProfileForm(data.profile);
        } else {
            modalBody.innerHTML = `<div class="error-message">Error: ${data.error}</div>`;
        }
    } catch (error) {
        modalBody.innerHTML = `<div class="error-message">Error de conexión</div>`;
        console.error('Error:', error);
    }
}

function renderProfileForm(profile) {
    const modalBody = document.getElementById('profileModalBody');
    if (!modalBody) return;
    
    const defaultAvatar = '/static/images/default.jpg';
    const timestamp = Date.now();
    const avatarUrl = (profile.avatar_url || defaultAvatar) + '?t=' + timestamp;
    
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
                <input type="text" value="${escapeHtml(profile.username)}" readonly class="readonly-field">
                <small class="field-note">No se puede modificar</small>
            </div>
            
            <div class="form-group">
                <label>Email</label>
                <input type="email" value="${escapeHtml(profile.email)}" readonly class="readonly-field">
                <small class="field-note">No se puede modificar</small>
            </div>
            
            <div class="form-group">
                <label for="displayName">Nombre para mostrar</label>
                <input type="text" 
                       id="displayName" 
                       name="display_name" 
                       value="${escapeHtml(profile.display_name || '')}" 
                       placeholder="Cómo quieres que te llamen">
            </div>
            
            <div class="form-group">
                <label for="bio">Biografía</label>
                <textarea id="bio" 
                          name="bio" 
                          rows="4" 
                          placeholder="Cuéntanos algo sobre ti...">${escapeHtml(profile.bio || '')}</textarea>
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
}

async function saveProfile(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    const data = {
        display_name: formData.get('display_name'),
        bio: formData.get('bio'),
        privacy_level: formData.get('privacy_level')
    };
    
    try {
        const response = await fetch('/api/profile/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Perfil actualizado', 'Los cambios se guardaron correctamente', 'success');
            
            // Actualizar nombre en el header
            if (data.display_name) {
                const profileNameEl = document.querySelector('.profile-name');
                if (profileNameEl) profileNameEl.textContent = data.display_name;
            }
            
            closeProfileModal();
        } else {
            showNotification('Error', result.error || 'No se pudo guardar', 'error');
        }
    } catch (error) {
        showNotification('Error', 'No se pudo guardar el perfil', 'error');
        console.error('Error:', error);
    }
}

function closeProfileModal() {
    const modal = document.getElementById('profileModal');
    const overlay = document.getElementById('modalOverlay');
    
    if (modal) modal.style.display = 'none';
    if (overlay) overlay.style.display = 'none';
}

// ============================================
// MODAL DE AVATAR
// ============================================

function showAvatarModal() {
    const modalBody = document.querySelector('#profileModal .modal-body');
    if (!modalBody) return;
    
    const defaultAvatar = '/static/images/default.jpg';
    const timestamp = Date.now();
    // Usar sessionStorage para obtener la última URL del avatar si está disponible
    const savedAvatar = sessionStorage.getItem('lastAvatarUrl') || currentProfile?.avatar_url || defaultAvatar;
    const avatarUrl = savedAvatar + (savedAvatar.includes('?') ? '&' : '?') + 't=' + timestamp;
    
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
                    <button class="btn-primary" onclick="uploadAvatar()" id="uploadBtn">
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
}

function handleAvatarSelected(input) {
    if (!input.files || !input.files[0]) return;
    
    const file = input.files[0];
    
    const validTypes = ['image/jpeg', 'image/png', 'image/gif'];
    if (!validTypes.includes(file.type)) {
        showNotification('Error', 'Formato no válido. Usa JPG, PNG o GIF', 'error');
        input.value = '';
        return;
    }
    
    if (file.size > 2 * 1024 * 1024) {
        showNotification('Error', 'La imagen no puede superar los 2MB', 'error');
        input.value = '';
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        document.getElementById('avatarPreview').src = e.target.result;
        document.getElementById('avatarPreviewContainer').style.display = 'block';
        document.querySelector('.upload-controls').style.display = 'none';
    };
    reader.readAsDataURL(file);
    
    window.selectedAvatarFile = file;
}

function cancelAvatarUpload() {
    document.getElementById('avatarPreviewContainer').style.display = 'none';
    document.querySelector('.upload-controls').style.display = 'block';
    document.getElementById('avatarInput').value = '';
    window.selectedAvatarFile = null;
}

// Función para cerrar el modal de avatar y volver al formulario de perfil
function closeAvatarModal() {
    if (currentProfile) {
        renderProfileForm(currentProfile);
    }
}

// Función para cargar los datos del perfil y mostrar el modal
async function loadProfileAndShowModal() {
    try {
        const response = await fetch('/api/profile/me');
        const data = await response.json();
        
        if (data.success) {
            currentProfile = data.profile;
            renderProfileForm(data.profile);
        }
    } catch (error) {
        console.error('Error recargando perfil:', error);
    }
}

async function uploadAvatar() {
    if (!window.selectedAvatarFile) return;
    
    const formData = new FormData();
    formData.append('avatar', window.selectedAvatarFile);
    
    const uploadBtn = document.getElementById('uploadBtn');
    const progressContainer = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('uploadProgressBar');
    const statusEl = document.getElementById('uploadStatus');
    
    uploadBtn.disabled = true;
    progressContainer.style.display = 'block';
    
    try {
        const response = await fetch('/api/profile/avatar', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            progressBar.style.width = '100%';
            statusEl.textContent = '¡Completado!';
            
            const timestamp = Date.now();
            const avatarUrl = result.avatar_url + '?t=' + timestamp;
            
            // 1. Actualizar avatar en el menú lateral (buscar por id común)
            const menuAvatar = document.getElementById('avatar-img');
            if (menuAvatar) {
                menuAvatar.src = avatarUrl;
            }
            
            // 2. Actualizar avatar en el modal de perfil
            const profileAvatarPreview = document.getElementById('profileAvatarPreview');
            if (profileAvatarPreview) {
                profileAvatarPreview.src = avatarUrl;
            }
            
            // 3. Actualizar cualquier otra imagen de avatar en la página
            document.querySelectorAll('.profile-avatar, .avatar-preview-large, [class*="avatar"]').forEach(img => {
                if (img.id !== 'avatar-img' && img.tagName === 'IMG') {
                    img.src = avatarUrl;
                }
            });
            
            // 4. Guardar la nueva URL en sessionStorage para persistencia
            sessionStorage.setItem('lastAvatarUrl', avatarUrl);
            
            // 5. Actualizar el perfil local con el nuevo avatar
            if (currentProfile) {
                currentProfile.avatar_url = result.avatar_url;
            }
            
            showNotification('Éxito', 'Avatar actualizado correctamente', 'success');
            
            // Cerrar modal de avatar y recargar datos del perfil
            closeAvatarModal();
            
            // Recargar datos del perfil y mostrar modal
            setTimeout(async () => {
                await loadProfileAndShowModal();
            }, 300);
        } else {
            throw new Error(result.error || 'Error al subir avatar');
        }
    } catch (error) {
        progressContainer.style.display = 'none';
        showNotification('Error', error.message, 'error');
        uploadBtn.disabled = false;
    }
}

// ============================================
// OTROS MODALES
// ============================================

function showSettingsModal() {
    const modal = document.getElementById('settingsModal');
    const overlay = document.getElementById('modalOverlay');
    
    // Cerrar dropdown
    const menu = document.getElementById('profileMenu');
    if (menu) menu.classList.remove('show');
    
    if (modal) modal.style.display = 'block';
    if (overlay) overlay.style.display = 'block';
}

function closeSettingsModal() {
    const modal = document.getElementById('settingsModal');
    const overlay = document.getElementById('modalOverlay');
    
    if (modal) modal.style.display = 'none';
    if (overlay) overlay.style.display = 'none';
}

function showWatchlistModal() {
    const modal = document.getElementById('watchlistModal');
    const overlay = document.getElementById('modalOverlay');
    
    // Cerrar dropdown
    const menu = document.getElementById('profileMenu');
    if (menu) menu.classList.remove('show');
    
    if (modal) modal.style.display = 'block';
    if (overlay) overlay.style.display = 'block';
}

function closeWatchlistModal() {
    const modal = document.getElementById('watchlistModal');
    const overlay = document.getElementById('modalOverlay');
    
    if (modal) modal.style.display = 'none';
    if (overlay) overlay.style.display = 'none';
}

// ============================================
// UTILIDADES
// ============================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Inicializar
document.addEventListener('DOMContentLoaded', function() {
    
});
