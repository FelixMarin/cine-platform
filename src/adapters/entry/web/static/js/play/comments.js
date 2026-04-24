/**
 * Módulo de comentarios para la página de reproducción
 * Maneja la carga, publicación, edición, eliminación y likes de comentarios
 */

class CommentsModule {
    constructor(movieId, movieTitle, tmdbId = null) {
        this.movieId = movieId || null;
        this.movieTitle = movieTitle;
        this.tmdbId = tmdbId;
        this.currentPage = 0;
        this.loading = false;
        this.hasMore = true;
        this.limit = 20;
        this.isAuthenticated = false;
        
        // Verificar autenticación
        this.checkAuth();
    }

    checkAuth() {
        // Verificar si el usuario está autenticado
        const userIdElement = document.getElementById('userId');
        this.isAuthenticated = userIdElement && parseInt(userIdElement.value) > 0;
    }

    async loadComments(append = false) {
        if (this.loading) return;
        this.loading = true;
        
        const offset = append ? this.currentPage * this.limit : 0;
        
        try {
            const response = await fetch(
                `/api/movie/comments?movie_id=${this.movieId}&limit=${this.limit}&offset=${offset}`
            );
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Error al cargar comentarios');
            }
            
            const data = await response.json();
            
            if (!append) {
                this.renderComments(data.comments);
                this.currentPage = 1;
                this.updateCommentCount(data.total);
            } else {
                this.appendComments(data.comments);
                this.currentPage++;
            }
            
            this.hasMore = data.has_more;
            this.updateLoadMoreButton();
        } catch (error) {
            console.error('Error loading comments:', error);
            this.showError('No se pudieron cargar los comentarios');
        } finally {
            this.loading = false;
        }
    }

    async addComment(commentText, isSpoiler = false, parentId = null) {
        if (!this.isAuthenticated) {
            this.showError('Debes iniciar sesión para comentar');
            return false;
        }

        try {
            const response = await fetch('/api/movie/comment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    movie_id: this.movieId,
                    movie_title: this.movieTitle,
                    tmdb_id: this.tmdbId,
                    comment_text: commentText,
                    is_spoiler: isSpoiler,
                    parent_comment_id: parentId
                })
            });

            if (response.ok) {
                const newComment = await response.json();
                
                if (parentId) {
                    // Es una respuesta, agregar al contenedor de respuestas
                    this.appendReply(parentId, newComment);
                } else {
                    // Es un comentario principal, agregar al inicio
                    this.prependComment(newComment);
                }
                
                // Limpiar formulario
                const form = parentId 
                    ? document.querySelector(`#reply-form-${parentId}`)
                    : document.getElementById('commentForm');
                if (form) {
                    const textarea = form.querySelector('textarea');
                    if (textarea) textarea.value = '';
                    const spoilerCheckbox = form.querySelector('input[type="checkbox"]');
                    if (spoilerCheckbox) spoilerCheckbox.checked = false;
                }
                
                // Cerrar formulario de respuesta si existe
                if (parentId) {
                    this.closeReplyForm(parentId);
                }
                
                // Actualizar contador
                const countElement = document.getElementById('commentCount');
                if (countElement) {
                    countElement.textContent = parseInt(countElement.textContent || '0') + 1;
                }
                
                return true;
            }
            
            const error = await response.json();
            this.showError(error.error || 'Error al publicar');
            return false;
        } catch (error) {
            console.error('Error adding comment:', error);
            this.showError('Error al publicar comentario');
            return false;
        }
    }

    async editComment(commentId, newText, isSpoiler) {
        if (!this.isAuthenticated) {
            this.showError('Debes iniciar sesión para editar');
            return false;
        }

        try {
            const response = await fetch(`/api/movie/comment/${commentId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    comment_text: newText,
                    is_spoiler: isSpoiler
                })
            });

            if (response.ok) {
                const updatedComment = await response.json();
                this.updateCommentInDom(commentId, updatedComment);
                return true;
            }
            
            const error = await response.json();
            this.showError(error.error || 'Error al editar');
            return false;
        } catch (error) {
            console.error('Error editing comment:', error);
            this.showError('Error al editar comentario');
            return false;
        }
    }

    async deleteComment(commentId) {
        if (!this.isAuthenticated) {
            this.showError('Debes iniciar sesión para eliminar');
            return false;
        }

        if (!confirm('¿Estás seguro de que quieres eliminar este comentario?')) {
            return false;
        }

        try {
            const response = await fetch(`/api/movie/comment/${commentId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.removeCommentFromDom(commentId);
                return true;
            }
            
            const error = await response.json();
            this.showError(error.error || 'Error al eliminar');
            return false;
        } catch (error) {
            console.error('Error deleting comment:', error);
            this.showError('Error al eliminar comentario');
            return false;
        }
    }

    async toggleLike(commentId) {
        if (!this.isAuthenticated) {
            this.showError('Debes iniciar sesión para dar like');
            return;
        }

        try {
            const response = await fetch(`/api/movie/comment/${commentId}/like`, {
                method: 'POST'
            });

            if (response.ok) {
                const data = await response.json();
                this.updateLikeCount(commentId, data.likes_count, data.liked);
            } else {
                const error = await response.json();
                this.showError(error.error || 'Error al dar like');
            }
        } catch (error) {
            console.error('Error toggling like:', error);
        }
    }

    async reportComment(commentId, reason) {
        if (!this.isAuthenticated) {
            this.showError('Debes iniciar sesión para reportar');
            return false;
        }

        if (!reason || reason.trim().length < 5) {
            this.showError('El motivo del reporte debe tener al menos 5 caracteres');
            return false;
        }

        try {
            const response = await fetch(`/api/movie/comment/${commentId}/report`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason })
            });

            if (response.ok) {
                alert('Comentario reportado correctamente. Gracias por tu colaboración.');
                return true;
            }
            
            const error = await response.json();
            this.showError(error.error || 'Error al reportar');
            return false;
        } catch (error) {
            console.error('Error reporting comment:', error);
            this.showError('Error al reportar comentario');
            return false;
        }
    }

    // === Métodos de renderizado ===

    renderComments(comments) {
        const container = document.getElementById('commentsList');
        if (!container) return;
        
        if (!comments || comments.length === 0) {
            container.innerHTML = this.renderEmptyState();
            return;
        }
        
        container.innerHTML = comments.map(comment => this.renderCommentHtml(comment)).join('');
        this.bindCommentActions();
    }

    appendComments(comments) {
        const container = document.getElementById('commentsList');
        if (!container) return;
        
        // Verificar si hay estado vacío
        const emptyState = container.querySelector('.no-comments');
        if (emptyState) {
            emptyState.remove();
        }
        
        container.innerHTML += comments.map(comment => this.renderCommentHtml(comment)).join('');
        this.bindCommentActions();
    }

    prependComment(comment) {
        const container = document.getElementById('commentsList');
        if (!container) return;
        
        // Verificar si hay estado vacío
        const emptyState = container.querySelector('.no-comments');
        if (emptyState) {
            emptyState.remove();
        }
        
        container.insertAdjacentHTML('afterbegin', this.renderCommentHtml(comment));
        this.bindCommentActions();
    }

    appendReply(parentId, reply) {
        const repliesContainer = document.querySelector(`.replies-container[data-parent-id="${parentId}"]`);
        if (repliesContainer) {
            const replyHtml = this.renderCommentHtml(reply, true);
            repliesContainer.insertAdjacentHTML('beforeend', replyHtml);
            this.bindCommentActions();
        }
    }

    renderCommentHtml(comment, isReply = false) {
        const spoilerClass = comment.is_spoiler ? 'spoiler' : '';
        const hiddenClass = comment.is_hidden ? 'hidden' : '';
        
        return `
            <div class="comment ${spoilerClass} ${hiddenClass}" data-comment-id="${comment.id}">
                <div class="comment-header">
                    <img class="comment-avatar" 
                         src="${comment.avatar_url || '/static/images/default-avatar.jpg'}" 
                         alt="${this.escapeHtml(comment.username)}"
                         onerror="this.src='/static/images/default-avatar.jpg'">
                    <span class="comment-author">${this.escapeHtml(comment.username)}</span>
                    <span class="comment-time">${this.formatDate(comment.created_at)}</span>
                    ${comment.is_edited ? '<span class="comment-edited">(editado)</span>' : ''}
                    ${comment.is_spoiler ? '<span class="spoiler-badge">⚠️ SPOILER</span>' : ''}
                    ${comment.is_hidden ? `<span class="hidden-badge">🚫 ${this.escapeHtml(comment.hidden_reason || 'Oculto')}</span>` : ''}
                </div>
                <div class="comment-content" data-comment-text="${this.escapeHtml(comment.comment_text)}">
                    ${comment.is_spoiler 
                        ? `<span class="spoiler-warning">⚠️ Este comentario contiene spoiler. Haz clic para ver.</span>` 
                        : this.escapeHtml(comment.comment_text)}
                </div>
                <div class="comment-actions">
                    <button class="like-btn ${comment.user_liked ? 'liked' : ''}" data-comment-id="${comment.id}">
                        👍 <span class="like-count">${comment.likes_count || 0}</span>
                    </button>
                    <button class="reply-btn" data-comment-id="${comment.id}">💬 Responder</button>
                    ${comment.can_edit ? `<button class="edit-btn" data-comment-id="${comment.id}">✏️ Editar</button>` : ''}
                    ${comment.can_delete ? `<button class="delete-btn" data-comment-id="${comment.id}">🗑️ Eliminar</button>` : ''}
                    <button class="report-btn" data-comment-id="${comment.id}">⚠️ Reportar</button>
                </div>
                
                ${this.renderReplyForm(comment.id)}
                
                ${this.renderEditForm(comment)}
                
                ${this.renderReportForm(comment.id)}
                
                <div class="replies-container" data-parent-id="${comment.id}">
                    ${comment.replies && comment.replies.length > 0 
                        ? comment.replies.map(reply => this.renderCommentHtml(reply, true)).join('') 
                        : ''}
                </div>
            </div>
        `;
    }

    renderEmptyState() {
        return `
            <div class="no-comments">
                <p>No hay comentarios aún. ¡Sé el primero en comentar!</p>
            </div>
        `;
    }

    renderReplyForm(commentId) {
        if (!this.isAuthenticated) return '';
        
        return `
            <div class="reply-form-container" id="reply-form-${commentId}" style="display: none;">
                <div class="reply-form">
                    <textarea placeholder="Escribe tu respuesta..." rows="2"></textarea>
                    <div class="reply-options">
                        <label>
                            <input type="checkbox"> ⚠️ Contiene spoiler
                        </label>
                        <div class="reply-buttons">
                            <button class="btn-cancel" data-cancel-reply="${commentId}">Cancelar</button>
                            <button class="btn-submit-reply" data-submit-reply="${commentId}">Responder</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderEditForm(comment) {
        if (!this.isAuthenticated || !comment.can_edit) return '';
        
        return `
            <div class="edit-form-container" id="edit-form-${comment.id}" style="display: none;">
                <div class="edit-form">
                    <textarea rows="3">${this.escapeHtml(comment.comment_text)}</textarea>
                    <div class="edit-options">
                        <label>
                            <input type="checkbox" ${comment.is_spoiler ? 'checked' : ''}> ⚠️ Contiene spoiler
                        </label>
                        <div class="edit-buttons">
                            <button class="btn-cancel" data-cancel-edit="${comment.id}">Cancelar</button>
                            <button class="btn-submit-edit" data-submit-edit="${comment.id}">Guardar</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderReportForm(commentId) {
        if (!this.isAuthenticated) return '';
        
        return `
            <div class="report-form-container" id="report-form-${commentId}" style="display: none;">
                <div class="report-form">
                    <h4>Reportar comentario</h4>
                    <select class="report-reason">
                        <option value="">Selecciona un motivo</option>
                        <option value="Contenido ofensivo">Contenido ofensivo</option>
                        <option value="Spam">Spam</option>
                        <option value="Spoiler no marcado">Spoiler no marcado</option>
                        <option value="Información falsa">Información falsa</option>
                        <option value="Otro">Otro</option>
                    </select>
                    <textarea placeholder="Describe el problema..." rows="2"></textarea>
                    <div class="report-buttons">
                        <button class="btn-cancel" data-cancel-report="${commentId}">Cancelar</button>
                        <button class="btn-submit-report" data-submit-report="${commentId}">Reportar</button>
                    </div>
                </div>
            </div>
        `;
    }

    // === Manipulación del DOM ===

    updateCommentInDom(commentId, updatedComment) {
        const commentElement = document.querySelector(`.comment[data-comment-id="${commentId}"]`);
        if (commentElement) {
            const newHtml = this.renderCommentHtml({
                ...updatedComment,
                can_edit: this.isAuthenticated,
                can_delete: this.isAuthenticated,
                user_liked: false
            });
            commentElement.outerHTML = newHtml;
            this.bindCommentActions();
        }
    }

    removeCommentFromDom(commentId) {
        const commentElement = document.querySelector(`.comment[data-comment-id="${commentId}"]`);
        if (commentElement) {
            commentElement.remove();
            
            // Verificar si no quedan comentarios
            const container = document.getElementById('commentsList');
            if (container && container.children.length === 0) {
                container.innerHTML = this.renderEmptyState();
            }
        }
    }

    updateLikeCount(commentId, count, liked) {
        const likeBtn = document.querySelector(`.like-btn[data-comment-id="${commentId}"]`);
        if (likeBtn) {
            const countSpan = likeBtn.querySelector('.like-count');
            if (countSpan) countSpan.textContent = count;
            
            if (liked) {
                likeBtn.classList.add('liked');
            } else {
                likeBtn.classList.remove('liked');
            }
        }
    }

    updateCommentCount(total) {
        const countElement = document.getElementById('commentCount');
        if (countElement) {
            countElement.textContent = total;
        }
    }

    updateLoadMoreButton() {
        const loadMoreBtn = document.getElementById('loadMoreComments');
        if (loadMoreBtn) {
            loadMoreBtn.style.display = this.hasMore ? 'block' : 'none';
        }
    }

    showReplyForm(commentId) {
        // Cerrar cualquier formulario de respuesta abierto
        document.querySelectorAll('.reply-form-container').forEach(el => {
            el.style.display = 'none';
        });
        
        const form = document.getElementById(`reply-form-${commentId}`);
        if (form) {
            form.style.display = 'block';
            const textarea = form.querySelector('textarea');
            if (textarea) textarea.focus();
        }
    }

    closeReplyForm(commentId) {
        const form = document.getElementById(`reply-form-${commentId}`);
        if (form) {
            form.style.display = 'none';
        }
    }

    showEditForm(commentId) {
        // Cerrar cualquier formulario de edición abierto
        document.querySelectorAll('.edit-form-container').forEach(el => {
            el.style.display = 'none';
        });
        
        const form = document.getElementById(`edit-form-${commentId}`);
        if (form) {
            form.style.display = 'block';
            const textarea = form.querySelector('textarea');
            if (textarea) textarea.focus();
        }
    }

    closeEditForm(commentId) {
        const form = document.getElementById(`edit-form-${commentId}`);
        if (form) {
            form.style.display = 'none';
        }
    }

    showReportForm(commentId) {
        // Cerrar cualquier formulario de reporte abierto
        document.querySelectorAll('.report-form-container').forEach(el => {
            el.style.display = 'none';
        });
        
        const form = document.getElementById(`report-form-${commentId}`);
        if (form) {
            form.style.display = 'block';
        }
    }

    closeReportForm(commentId) {
        const form = document.getElementById(`report-form-${commentId}`);
        if (form) {
            form.style.display = 'none';
        }
    }

    // === Binding de eventos ===

    bindCommentActions() {
        // Botones de like
        document.querySelectorAll('.like-btn').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                const commentId = parseInt(btn.dataset.commentId);
                this.toggleLike(commentId);
            };
        });

        // Botones de responder
        document.querySelectorAll('.reply-btn').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                const commentId = parseInt(btn.dataset.commentId);
                this.showReplyForm(commentId);
            };
        });

        // Botones de editar
        document.querySelectorAll('.edit-btn').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                const commentId = parseInt(btn.dataset.commentId);
                this.showEditForm(commentId);
            };
        });

        // Botones de eliminar
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                const commentId = parseInt(btn.dataset.commentId);
                this.deleteComment(commentId);
            };
        });

        // Botones de reportar
        document.querySelectorAll('.report-btn').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                const commentId = parseInt(btn.dataset.commentId);
                this.showReportForm(commentId);
            };
        });

        // Cancelar respuesta
        document.querySelectorAll('[data-cancel-reply]').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                const commentId = parseInt(btn.dataset.cancelReply);
                this.closeReplyForm(commentId);
            };
        });

        // Enviar respuesta
        document.querySelectorAll('[data-submit-reply]').forEach(btn => {
            btn.onclick = async (e) => {
                e.stopPropagation();
                const commentId = parseInt(btn.dataset.submitReply);
                const form = document.getElementById(`reply-form-${commentId}`);
                if (form) {
                    const textarea = form.querySelector('textarea');
                    const checkbox = form.querySelector('input[type="checkbox"]');
                    const text = textarea.value.trim();
                    const isSpoiler = checkbox.checked;
                    
                    if (text.length >= 3) {
                        await this.addComment(text, isSpoiler, commentId);
                    } else {
                        this.showError('La respuesta debe tener al menos 3 caracteres');
                    }
                }
            };
        });

        // Cancelar edición
        document.querySelectorAll('[data-cancel-edit]').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                const commentId = parseInt(btn.dataset.cancelEdit);
                this.closeEditForm(commentId);
            };
        });

        // Guardar edición
        document.querySelectorAll('[data-submit-edit]').forEach(btn => {
            btn.onclick = async (e) => {
                e.stopPropagation();
                const commentId = parseInt(btn.dataset.submitEdit);
                const form = document.getElementById(`edit-form-${commentId}`);
                if (form) {
                    const textarea = form.querySelector('textarea');
                    const checkbox = form.querySelector('input[type="checkbox"]');
                    const text = textarea.value.trim();
                    const isSpoiler = checkbox.checked;
                    
                    if (text.length >= 3) {
                        await this.editComment(commentId, text, isSpoiler);
                    } else {
                        this.showError('El comentario debe tener al menos 3 caracteres');
                    }
                }
            };
        });

        // Cancelar reporte
        document.querySelectorAll('[data-cancel-report]').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                const commentId = parseInt(btn.dataset.cancelReport);
                this.closeReportForm(commentId);
            };
        });

        // Enviar reporte
        document.querySelectorAll('[data-submit-report]').forEach(btn => {
            btn.onclick = async (e) => {
                e.stopPropagation();
                const commentId = parseInt(btn.dataset.submitReport);
                const form = document.getElementById(`report-form-${commentId}`);
                if (form) {
                    const select = form.querySelector('.report-reason');
                    const textarea = form.querySelector('textarea');
                    
                    let reason = select.value;
                    if (reason === 'Otro' && textarea.value.trim()) {
                        reason = textarea.value.trim();
                    }
                    
                    if (reason) {
                        await this.reportComment(commentId, reason);
                        this.closeReportForm(commentId);
                    } else {
                        this.showError('Por favor selecciona un motivo');
                    }
                }
            };
        });

        // Manejo de spoilers
        document.querySelectorAll('.comment.spoiler .comment-content').forEach(content => {
            content.onclick = () => {
                content.classList.toggle('revealed');
            };
        });
    }

    // === Utilidades ===

    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) return 'Hace un momento';
        if (minutes < 60) return `Hace ${minutes}m`;
        if (hours < 24) return `Hace ${hours}h`;
        if (days < 7) return `Hace ${days}d`;
        
        return date.toLocaleDateString('es-ES', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showError(message) {
        // Crear notificación de error
        const notification = document.createElement('div');
        notification.className = 'notification error';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #e74c3c;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 10000;
            animation: fadeIn 0.3s;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Inicialización cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    const movieIdElement = document.getElementById('movieId');
    const movieTitleElement = document.getElementById('movieTitle');
    
    if (movieIdElement && movieTitleElement) {
        const movieId = movieIdElement.value ? parseInt(movieIdElement.value, 10) : null;
        
        if (!movieId) {
            console.warn('movieId no está disponible, las funciones de comentarios estarán limitadas');
        }
        
        window.commentsModule = new CommentsModule(
            movieId,
            movieTitleElement.value,
            document.getElementById('tmdbId')?.value || null
        );
        
        // Cargar comentarios iniciales solo si tenemos movieId
        if (movieId) {
            window.commentsModule.loadComments();
        }
        
        // Configurar botón de cargar más
        const loadMoreBtn = document.getElementById('loadMoreComments');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', () => {
                if (movieId) {
                    window.commentsModule.loadComments(true);
                }
            });
        }
        
        // Configurar formulario principal de comentario
        const submitBtn = document.getElementById('submitComment');
        const commentText = document.getElementById('commentText');
        const commentSpoiler = document.getElementById('commentSpoiler');
        
        if (submitBtn && commentText) {
            submitBtn.addEventListener('click', async () => {
                const text = commentText.value.trim();
                const isSpoiler = commentSpoiler?.checked || false;
                
                if (text.length < 3) {
                    window.commentsModule.showError('El comentario debe tener al menos 3 caracteres');
                    return;
                }
                
                if (!movieId) {
                    window.commentsModule.showError('No se pueden publicar comentarios sin ID de película');
                    return;
                }
                
                const success = await window.commentsModule.addComment(text, isSpoiler);
                if (success) {
                    commentText.value = '';
                    if (commentSpoiler) commentSpoiler.checked = false;
                }
            });
        }
    }
});

// Exportar para uso en otros módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CommentsModule;
}