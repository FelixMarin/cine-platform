/**
 * Torrent Optimize - Modal UI
 * UI del modal: createOptimizeModal, showOptimizeModal, closeModal, submitOptimization
 */
(function() {
    'use strict';

    // Inicializar el objeto si no existe
    window.TorrentOptimize = window.TorrentOptimize || {};

    /**
     * Crea el modal de optimización
     * @returns {HTMLElement}
     */
    window.TorrentOptimize.createOptimizeModal = function() {
        var modal = document.createElement('div');
        modal.id = 'torrent-optimize-modal';
        modal.className = 'modal';

        modal.innerHTML = 
            '<div class="modal-content">' +
                '<div class="modal-header">' +
                    '<h2>🚀 Optimizar Torrent</h2>' +
                    '<button class="modal-close" onclick="TorrentOptimize.closeModal()">&times;</button>' +
                '</div>' +
                '<div class="modal-body">' +
                '<div class="torrent-info">' +
                    '<p><strong>Archivo original:</strong> <span id="optimize-torrent-name">-</span></p>' +
                    '<p><strong>Tamaño:</strong> <span id="optimize-torrent-size">-</span></p>' +
                    '<p><strong>GPU:</strong> <span id="optimize-gpu-status">Verificando...</span></p>' +
                '</div>' +
                
                '<div class="form-group">' +
                    '<label for="optimize-category">Categoría:</label>' +
                    '<select id="optimize-category" class="form-control">' +
                        '<option value="action">Acción</option>' +
                        '<option value="comedia">Comedia</option>' +
                        '<option value="drama">Drama</option>' +
                        '<option value="terror">Terror</option>' +
                        '<option value="sci_fi">Ciencia Ficción</option>' +
                        '<option value="animacion">Animación</option>' +
                        '<option value="documental">Documental</option>' +
                        '<option value="otro">Otro</option>' +
                        '<option value="aventura">Aventura</option>' +
                        '<option value="familia">Familia</option>' +
                        '<option value="fantasia">Fantasía</option>' +
                        '<option value="suspense">Suspense</option>' +
                        '<option value="romance">Romance</option>' +
                    '</select>' +
                '</div>' +

                '<div class="form-group">' +
                    '<label for="optimize-output-filename">Nombre de salida:</label>' +
                    '<input type="text" id="optimize-output-filename" class="form-control" placeholder="Nombre del archivo optimizado">' +
                    '<small class="form-text text-muted" id="extension-hint"></small>' +
                '</div>' +
                    
                    '<input type="hidden" id="optimize-torrent-id">' +
                    
                    '<div id="optimize-progress-container" class="progress-container" style="display: none;">' +
                        '<div class="progress-bar">' +
                            '<div id="optimize-progress-bar" class="progress-fill" style="width: 0%"></div>' +
                        '</div>' +
                        '<div class="progress-text">' +
                            '<span id="optimize-progress-text">0%</span>' +
                            '<span id="optimize-progress-status">Iniciando...</span>' +
                        '</div>' +
                        '<div id="optimize-eta" class="eta-text"></div>' +
                    '</div>' +
                '</div>' +
                '<div class="modal-footer">' +
                    '<button class="btn btn-secondary" onclick="TorrentOptimize.closeModal()">Cancelar</button>' +
                    '<button class="btn btn-primary" id="btn-start-optimize" onclick="TorrentOptimize.submitOptimization()">' +
                        '🚀 Iniciar Optimización' +
                    '</button>' +
                '</div>' +
            '</div>';

        return modal;
    };

    /**
     * Muestra el modal de optimización para un torrent
     * @param {Object} torrent - Información del torrent
     */
    window.TorrentOptimize.showOptimizeModal = function(torrent) {
        // Crear modal si no existe
        var modal = document.getElementById('torrent-optimize-modal');

        if (!modal) {
            modal = window.TorrentOptimize.createOptimizeModal();
            document.body.appendChild(modal);
        }

        var decodedName = decodeURIComponent(torrent.name);
        // Llenar información del torrent
        var nameEl = document.getElementById('optimize-torrent-name');
        var sizeEl = document.getElementById('optimize-torrent-size');
        var idEl = document.getElementById('optimize-torrent-id');
        var filenameInput = document.getElementById('optimize-output-filename');
        
        var sizeValue = parseInt(torrent.size, 10) || 0;
        if (nameEl) nameEl.textContent = decodedName || 'Sin nombre';
        if (sizeEl) sizeEl.textContent = (window.TorrentOptimize.formatSize ? window.TorrentOptimize.formatSize(sizeValue) : sizeValue + ' B');
        if (idEl) idEl.value = torrent.id;
        
        // Establecer nombre de archivo de salida por defecto (sin extensión, se añadirá después)
        if (filenameInput) {
            // Eliminar extensión existente si la tiene
            var baseName = decodedName.replace(/\.[^/.]+$/, '');
            filenameInput.value = baseName;
            filenameInput.placeholder = decodedName;
        }
        
        // Mostrar sugerencia de extensión automática
        var extensionHint = document.getElementById('extension-hint');
        if (extensionHint) {
            extensionHint.textContent = 'Se añadirá la extensión .mkv automáticamente';
        }

        // Mostrar modal (no bloqueante - permite scroll)
        modal.classList.add('active');
        document.body.style.overflow = 'auto';

        // Resetear el progreso
        var progressContainer = document.getElementById('optimize-progress-container');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
        
        var btn = document.getElementById('btn-start-optimize');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '🚀 Iniciar Optimización';
        }

        // Verificar GPU
        var checkGpuStatus = window.TorrentOptimize.checkGpuStatus;
        if (checkGpuStatus) {
            checkGpuStatus().then(function(result) {
                var gpuStatus = document.getElementById('optimize-gpu-status');
                if (result.success) {
                    if (result.gpu_available && result.gpu_name) {
                        if (gpuStatus) {
                            gpuStatus.textContent = '✅ ' + result.gpu_name + ' detectada';
                            gpuStatus.className = 'status-success';
                        }
                    } else {
                        if (gpuStatus) {
                            gpuStatus.textContent = '⚠️ Sin GPU (usando CPU)';
                            gpuStatus.className = 'status-warning';
                        }
                    }
                } else {
                    if (gpuStatus) {
                        gpuStatus.textContent = '❌ Error verificando GPU';
                        gpuStatus.className = 'status-error';
                    }
                }
            });
        }
    };

    /**
     * Cierra el modal de optimización
     */
    window.TorrentOptimize.closeModal = function() {
        var modal = document.getElementById('torrent-optimize-modal');
        if (modal) {
            modal.classList.remove('active');
        }

        // Permitir scroll (asegurar que no queda bloqueado)
        document.body.style.overflow = 'auto';

        // Resetear UI
        var progressContainer = document.getElementById('optimize-progress-container');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }

        var progressBar = document.getElementById('optimize-progress-bar');
        if (progressBar) {
            progressBar.style.width = '0%';
        }

        var btn = document.getElementById('btn-start-optimize');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '🚀 Iniciar Optimización';
        }
    };

    /**
     * Envía la solicitud de optimización
     */
    window.TorrentOptimize.submitOptimization = async function() {
        var authFetch = window.TorrentOptimize.authFetch;
        if (!authFetch) return;
        
        var torrentIdEl = document.getElementById('optimize-torrent-id');
        var categoryEl = document.getElementById('optimize-category');
        var filenameInput = document.getElementById('optimize-output-filename');
        
        var torrentId = torrentIdEl ? torrentIdEl.value : '';
        var category = categoryEl ? categoryEl.value : 'other';
        var filename = filenameInput ? filenameInput.value.trim() : '';

        if (!torrentId) {
            alert('ID de torrent inválido');
            return;
        }

        if (!filename) {
            alert('Por favor, ingresa un nombre para el archivo de salida');
            filenameInput.focus();
            return;
        }

        // Siempre añade extensión .mkv si no la tiene
        if (filename && filename.indexOf('.') === -1) {
            filename = filename + '.mkv';
        }

        

        var btn = document.getElementById('btn-start-optimize');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '⏳ Iniciando...';
        }

        try {
            var response = await authFetch('/api/optimize-torrent', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    torrent_id: torrentId, 
                    filename: filename,
                    category: category
                })
            });
            
            var result = await response.json();

            if (result.success) {
                

                // Cerrar modal inmediatamente
                if (window.TorrentOptimize.closeModal) {
                    window.TorrentOptimize.closeModal();
                }
                
                // Actualizar botón en downloads
                if (window.updateDownloadButton) {
                    window.updateDownloadButton(torrentId, '⏳ Optimizando');
                }
                
                // Mostrar notificación indicando dónde ver el progreso
                if (typeof showNotification === 'function') {
                    showNotification(
                        '⚡ Optimización iniciada', 
                        'El proceso se está ejecutando en segundo plano. Puedes ver el progreso en la pestaña "Optimizaciones".',
                        'success'
                    );
                }

                // Iniciar monitoreo en segundo plano
                if (window.TorrentOptimize.monitorOptimization) {
                    window.TorrentOptimize.monitorOptimization(result.process_id, torrentId);
                }
                
                // Intentar cambiar a la pestaña de optimizaciones si existe la función
                if (typeof switchTab === 'function') {
                    switchTab('optimizations');
                } else if (typeof window.switchToOptimizationsTab === 'function') {
                    window.switchToOptimizationsTab();
                }
            } else {
                throw new Error(result.error || 'Error desconocido');
            }
        } catch (error) {
            console.error('[TorrentOptimize] Error:', error);
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '🚀 Iniciar Optimización';
            }
            
            // Actualizar botón con error
            if (window.updateDownloadButton) {
                window.updateDownloadButton(torrentId, '❌ Error', true);
            }
            
            if (typeof showNotification === 'function') {
                showNotification('Error', error.message, 'error');
            } else {
                alert('Error: ' + error.message);
            }
        }
    };

})();
