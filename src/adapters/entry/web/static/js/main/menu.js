let isMenuCollapsed = false;

// Función helper para añadir cache busting a URLs
function addCacheBuster(url) {
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}_cb=${Date.now()}`;
}

function toggleMenu() {
    const menu = document.getElementById('sideMenu');
    const overlay = document.querySelector('.menu-overlay');

    if (menu && overlay) {
        menu.classList.toggle('open');
        overlay.classList.toggle('active');
    }
}

function toggleCollapse() {
    const menu = document.getElementById('sideMenu');
    const mainContent = document.getElementById('mainContent');
    const collapseBtn = document.querySelector('.menu-collapse-btn');

    if (!menu || !mainContent || !collapseBtn) return;

    isMenuCollapsed = !isMenuCollapsed;

    if (isMenuCollapsed) {
        menu.classList.add('collapsed');
        mainContent.classList.add('expanded');
        collapseBtn.innerHTML = '▶';
    } else {
        menu.classList.remove('collapsed');
        mainContent.classList.remove('expanded');
        collapseBtn.innerHTML = '◀';
    }

    try {
        localStorage.setItem('menuCollapsed', isMenuCollapsed);
    } catch (e) {
        console.warn('No se pudo guardar la preferencia', e);
    }
}

function loadSavedPreferences() {
    try {
        const savedMenuState = localStorage.getItem('menuCollapsed');

        if (savedMenuState !== null && window.innerWidth > 768) {
            isMenuCollapsed = savedMenuState === 'true';

            const menu = document.getElementById('sideMenu');
            const mainContent = document.getElementById('mainContent');
            const collapseBtn = document.querySelector('.menu-collapse-btn');

            if (menu && mainContent && collapseBtn) {
                if (isMenuCollapsed) {
                    menu.classList.add('collapsed');
                    mainContent.classList.add('expanded');
                    collapseBtn.innerHTML = '▶';
                } else {
                    menu.classList.remove('collapsed');
                    mainContent.classList.remove('expanded');
                    collapseBtn.innerHTML = '◀';
                }
            }
        }
    } catch (e) {
        console.warn('No se pudieron cargar las preferencias', e);
    }
}

function refreshWithAnimation(button) {
    // Añadir clase de carga
    button.classList.add('loading');

    // Cambiar texto opcionalmente
    const textSpan = button.querySelector('.refresh-text');
    const originalText = textSpan.textContent;
    textSpan.textContent = 'Actualizando...';

    // Llamar a la función de refresco
    window.refreshContent();

    // Quitar clase después de un tiempo (la función refreshContent ya recargará)
    setTimeout(() => {
        button.classList.remove('loading');
        textSpan.textContent = originalText;
    }, 1000);
}

// Función para sincronizar el catálogo con el sistema de archivos
async function syncCatalog(button) {
    // Añadir clase de carga
    button.classList.add('loading');

    // Cambiar texto
    const textSpan = button.querySelector('.refresh-text');
    const originalText = textSpan.textContent;
    textSpan.textContent = 'Sincronizando...';
    button.disabled = true;

    try {
        const response = await fetch(addCacheBuster('/api/catalog/sync'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Error al sincronizar');
        }

        const result = await response.json();
        

        // Mostrar notificación de éxito con detalles
        const addedCount = result.added_movies + result.added_series;
        const deletedCount = result.deleted_movies + result.deleted_series;
        let message = 'Sincronización completada';
        if (addedCount > 0 || deletedCount > 0) {
            message += `: ${addedCount} añadidos, ${deletedCount} eliminados`;
        }
        showNotification(message, 'success');

        // Invalidar caché
        window.invalidateCache();

        // Recargar página completamente para asegurar datos frescos
        // Esto es necesario porque el repositorio tiene caché interna
        window.location.reload();

    } catch (error) {
        console.error('❌ Error en sincronización:', error);
        showNotification('Error: ' + error.message, 'error');
    } finally {
        // Restaurar estado del botón
        button.classList.remove('loading');
        textSpan.textContent = originalText;
        button.disabled = false;
    }
}

// Función para mostrar notificaciones
function showNotification(message, type = 'info') {
    // Intentar usar el sistema de notificaciones existente
    if (window.showNotification) {
        window.showNotification(message, type);
        return;
    }

    // Fallback: crear notificación manualmente
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 5px;
        z-index: 10000;
        background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#2196F3'};
        color: white;
    `;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}

window.toggleMenu = toggleMenu;
window.toggleCollapse = toggleCollapse;
window.loadSavedPreferences = loadSavedPreferences;
window.refreshWithAnimation = refreshWithAnimation;
window.syncCatalog = syncCatalog;