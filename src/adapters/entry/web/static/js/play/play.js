/**
 * Manejador de errores de imágenes con proxies de fallback
 */
HTMLImageElement.prototype.handleError = function () {
    const proxies = JSON.parse(this.dataset.proxies || '[]');
    const currentSrc = this.src;
    const currentIndex = proxies.indexOf(currentSrc);
    const nextIndex = currentIndex + 1;

    if (nextIndex < proxies.length) {
        
        this.src = proxies[nextIndex];
    } else {
        
        this.src = '/static/images/default-poster.jpg';
        this.onerror = null;
    }
};

/**
 * Funcionalidad de "Me gusta" para películas
 */
(function() {
    'use strict';

    // Elementos del DOM
    const likeButton = document.getElementById('likeButton');
    
    // Datos de la película del elemento
    let movieId = null;
    let mediaPath = '';
    let movieTitle = '';

    /**
     * Inicializa la funcionalidad de like
     */
    function initLikeButton() {
        if (!likeButton) return;

        // Obtener datos del botón
        movieId = likeButton.dataset.movieId || null;
        mediaPath = likeButton.dataset.mediaPath || '';
        movieTitle = likeButton.dataset.title || '';

        // Añadir evento clic
        likeButton.addEventListener('click', handleLikeClick);

        // Cargar estado inicial
        loadLikeStatus();
    }

    /**
     * Carga el estado del like al iniciar la página
     */
    async function loadLikeStatus() {
        if (!movieId && !mediaPath && !movieTitle) {
            console.log('Like: No hay datos de película para cargar estado');
            return;
        }

        // Intentar primero obtener el movie_id de los datos disponibles
        await resolveMovieId();

        if (!movieId && !movieTitle) {
            console.log('Like: No se pudo resolver el ID del contenido');
            return;
        }

        try {
            const params = new URLSearchParams();
            if (movieId) {
                params.append('movie_id', movieId);
            }
            if (movieTitle) {
                params.append('title', movieTitle);
            }

            const response = await fetch(`/api/movie/like/status?${params.toString()}`);
            const data = await response.json();
            
            updateLikeButton(data.liked);
        } catch (error) {
            console.error('Like: Error cargando estado:', error);
        }
    }

    /**
     * Resuelve el movie_id a partir de los datos disponibles
     */
    async function resolveMovieId() {
        // Si tenemos movie_id directo, usarlo
        if (movieId) {
            return;
        }

        // Intentar obtener de la URL si es una ruta /play/id/<id>
        const pathMatch = window.location.pathname.match(/\/play\/id\/(\d+)/);
        if (pathMatch) {
            movieId = parseInt(pathMatch[1], 10);
            return;
        }

        // Si es una ruta /play/<path>, intentar buscar por título
        // El servidor ya tiene el título, lo usaremos en la llamada API
    }

    /**
     * Maneja el clic en el botón de like
     */
    async function handleLikeClick(event) {
        event.preventDefault();

        if (!movieId && !movieTitle) {
            console.error('Like: No hay información suficiente para dar like');
            showNotification('No se puede guardar el like', 'error');
            return;
        }

        const isLiked = likeButton.classList.contains('liked');
        
        // Deshabilitar botón durante la operación
        setLoading(true);

        try {
            if (isLiked) {
                // Eliminar like
                const params = new URLSearchParams();
                if (movieId) {
                    params.append('movie_id', movieId);
                } else if (movieTitle) {
                    params.append('title', movieTitle);
                }
                
                const response = await fetch(`/api/movie/like?${params.toString()}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    updateLikeButton(false);
                    showNotification('Has quitado tu me gusta', 'info');
                } else {
                    const data = await response.json();
                    showNotification(data.error || 'Error al quitar el like', 'error');
                }
            } else {
                // Guardar like - siempre enviar movie_title como fallback
                const requestBody = {
                    like_type: 'like'
                };
                
                if (movieId) {
                    requestBody.movie_id = movieId;
                }
                if (movieTitle) {
                    requestBody.movie_title = movieTitle;
                }
                
                const response = await fetch('/api/movie/like', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(requestBody)
                });
                
                if (response.ok) {
                    const data = await response.json();
                    // Actualizar el ID si viene en la respuesta
                    if (data.like_id) {
                        movieId = data.like_id;
                    }
                    updateLikeButton(true);
                    showNotification('¡Te ha gusta!', 'success');
                } else {
                    const data = await response.json();
                    showNotification(data.error || data.message || 'Error al guardar el like', 'error');
                }
            }
        } catch (error) {
            console.error('Like: Error en la operación:', error);
            showNotification('Error de conexión', 'error');
        } finally {
            setLoading(false);
        }
    }

    /**
     * Actualiza el estado visual del botón
     */
    function updateLikeButton(liked) {
        if (!likeButton) return;

        if (liked) {
            likeButton.classList.add('liked');
            likeButton.title = 'Ya no me gusta';
            likeButton.querySelector('.like-text').textContent = 'Te gusta';
            // Cambiar el ícono a sólido
            likeButton.querySelector('.like-icon').setAttribute('fill', 'currentColor');
        } else {
            likeButton.classList.remove('liked');
            likeButton.title = 'Me gusta esta película';
            likeButton.querySelector('.like-text').textContent = 'Me gusta';
            // Cambiar el ícono a outline
            likeButton.querySelector('.like-icon').setAttribute('fill', 'none');
        }
    }

    /**
     * Muestra/oculta el spinner de carga
     */
    function setLoading(loading) {
        if (!likeButton) return;

        const spinner = likeButton.querySelector('.like-spinner');
        const icon = likeButton.querySelector('.like-icon');
        const text = likeButton.querySelector('.like-text');

        if (loading) {
            likeButton.classList.add('loading');
            likeButton.disabled = true;
            if (spinner) spinner.style.display = 'inline';
            if (icon) icon.style.display = 'none';
            if (text) text.style.display = 'none';
        } else {
            likeButton.classList.remove('loading');
            likeButton.disabled = false;
            if (spinner) spinner.style.display = 'none';
            if (icon) icon.style.display = 'inline';
            if (text) text.style.display = 'inline';
        }
    }

    /**
     * Muestra una notificación toast
     */
    function showNotification(message, type) {
        // Crear elemento de notificación
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Estilos básicos
        notification.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 12px 24px;
            border-radius: 8px;
            color: white;
            font-family: system-ui, -apple-system, sans-serif;
            font-size: 14px;
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
            background-color: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#17a2b8'};
        `;

        // Añadir animación CSS si no existe
        if (!document.getElementById('notification-styles')) {
            const style = document.createElement('style');
            style.id = 'notification-styles';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(notification);

        // Eliminar después de 3 segundos
        setTimeout(() => {
            notification.style.animation = 'slideIn 0.3s ease-out reverse';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initLikeButton);
    } else {
        initLikeButton();
    }
})();
