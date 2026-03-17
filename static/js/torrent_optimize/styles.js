/**
 * Torrent Optimize - Styles
 * Inyección de CSS: addStyles
 */
(function() {
    'use strict';

    // Inicializar el objeto si no existe
    window.TorrentOptimize = window.TorrentOptimize || {};

    /**
     * Agrega estilos CSS necesarios
     */
    window.TorrentOptimize.addStyles = function() {
        if (document.getElementById('torrent-optimize-styles')) return;

        var styles = document.createElement('style');
        styles.id = 'torrent-optimize-styles';
        styles.textContent = 
            '.modal {' +
                'display: none;' +
                'position: fixed;' +
                'top: 0;' +
                'left: 0;' +
                'width: 100%;' +
                'height: 100%;' +
                'background: rgba(0, 0, 0, 0.7);' +
                'z-index: 9999;' +
                'align-items: center;' +
                'justify-content: center;' +
            '}' +
            
            '.modal.active {' +
                'display: flex;' +
            '}' +
            
            '.modal-content {' +
                'background: var(--bg-primary, #1a1a2e);' +
                'border-radius: 12px;' +
                'width: 90%;' +
                'max-width: 500px;' +
                'max-height: 90vh;' +
                'overflow-y: auto;' +
                'box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);' +
            '}' +
            
            '.modal-header {' +
                'display: flex;' +
                'justify-content: space-between;' +
                'align-items: center;' +
                'padding: 20px;' +
                'border-bottom: 1px solid var(--border-color, #333);' +
            '}' +
            
            '.modal-header h2 {' +
                'margin: 0;' +
                'font-size: 1.5rem;' +
                'color: var(--text-primary, #fff);' +
            '}' +
            
            '.modal-close {' +
                'background: none;' +
                'border: none;' +
                'color: var(--text-secondary, #aaa);' +
                'font-size: 2rem;' +
                'cursor: pointer;' +
                'line-height: 1;' +
            '}' +
            
            '.modal-close:hover {' +
                'color: var(--text-primary, #fff);' +
            '}' +
            
            '.modal-body {' +
                'padding: 20px;' +
            '}' +
            
            '.modal-footer {' +
                'padding: 20px;' +
                'border-top: 1px solid var(--border-color, #333);' +
                'display: flex;' +
                'justify-content: flex-end;' +
                'gap: 10px;' +
            '}' +
            
            '.torrent-info {' +
                'background: var(--bg-secondary, #16213e);' +
                'padding: 15px;' +
                'border-radius: 8px;' +
                'margin-bottom: 20px;' +
            '}' +
            
            '.torrent-info p {' +
                'margin: 5px 0;' +
                'color: var(--text-secondary, #aaa);' +
            '}' +
            
            '.torrent-info strong {' +
                'color: var(--text-primary, #fff);' +
            '}' +
            
            '.form-group {' +
                'margin-bottom: 20px;' +
            '}' +
            
            '.form-group label {' +
                'display: block;' +
                'margin-bottom: 8px;' +
                'color: var(--text-primary, #fff);' +
                'font-weight: 500;' +
            '}' +
            
            '.form-control {' +
                'width: 100%;' +
                'padding: 10px 15px;' +
                'border: 1px solid var(--border-color, #333);' +
                'border-radius: 6px;' +
                'background: var(--bg-secondary, #16213e);' +
                'color: var(--text-primary, #fff);' +
                'font-size: 1rem;' +
            '}' +
            
            '.form-control:focus {' +
                'outline: none;' +
                'border-color: var(--accent-primary, #4f46e5);' +
            '}' +
            
            '.progress-container {' +
                'margin-top: 20px;' +
            '}' +
            
            '.progress-bar {' +
                'height: 8px;' +
                'background: var(--bg-secondary, #16213e);' +
                'border-radius: 4px;' +
                'overflow: hidden;' +
            '}' +
            
            '.progress-fill {' +
                'height: 100%;' +
                'background: linear-gradient(90deg, #4f46e5, #06b6d4);' +
                'transition: width 0.3s ease;' +
            '}' +
            
            '.progress-text {' +
                'display: flex;' +
                'justify-content: space-between;' +
                'margin-top: 10px;' +
                'color: var(--text-secondary, #aaa);' +
                'font-size: 0.9rem;' +
            '}' +
            
            '.eta-text {' +
                'text-align: center;' +
                'margin-top: 10px;' +
                'color: var(--text-secondary, #aaa);' +
                'font-size: 0.85rem;' +
            '}' +
            
            '.status-success { color: #10b981; }' +
            '.status-warning { color: #f59e0b; }' +
            '.status-error { color: #ef4444; }' +
            
            '.btn {' +
                'padding: 10px 20px;' +
                'border: none;' +
                'border-radius: 6px;' +
                'font-size: 1rem;' +
                'cursor: pointer;' +
                'transition: all 0.2s;' +
            '}' +
            
            '.btn-primary {' +
                'background: linear-gradient(135deg, #4f46e5, #06b6d4);' +
                'color: white;' +
            '}' +
            
            '.btn-primary:hover {' +
                'transform: translateY(-2px);' +
                'box-shadow: 0 4px 15px rgba(79, 70, 229, 0.4);' +
            '}' +
            
            '.btn-primary:disabled {' +
                'opacity: 0.6;' +
                'cursor: not-allowed;' +
                'transform: none;' +
            '}' +
            
            '.btn-secondary {' +
                'background: var(--bg-secondary, #16213e);' +
                'color: var(--text-primary, #fff);' +
                'border: 1px solid var(--border-color, #333);' +
            '}' +
            
            '.btn-secondary:hover {' +
                'background: var(--bg-tertiary, #1f2937);' +
            '}' +
            
            '/* ESTADOS DEL BOTÓN GPU OPTIMIZE */' +
            '.btn-optimize {' +
                'background-color: #28a745;' +
                'color: white;' +
                'border: none;' +
                'padding: 5px 10px;' +
                'border-radius: 3px;' +
                'cursor: pointer;' +
                'transition: all 0.2s ease;' +
                'font-size: 0.9rem;' +
            '}' +
            
            '.btn-optimize:hover {' +
                'background-color: #218838;' +
            '}' +
            
            '.btn-optimize.optimizing {' +
                'background-color: #ffc107;' +
                'color: #212529;' +
                'cursor: not-allowed;' +
                'opacity: 0.8;' +
            '}' +
            
            '.btn-optimize.optimizing:hover {' +
                'background-color: #ffc107;' +
            '}' +
            
            '.btn-optimize.optimized {' +
                'background-color: #6c757d;' +
                'color: white;' +
                'cursor: not-allowed;' +
                'opacity: 0.6;' +
            '}' +
            
            '.btn-optimize.optimized:hover {' +
                'background-color: #6c757d;' +
            '}' +
            
            '.btn-optimize.error {' +
                'background-color: #dc3545;' +
                'color: white;' +
            '}' +
            
            '.btn-optimize.error:hover {' +
                'background-color: #c82333;' +
            '}' +
            
            '.btn-optimize:disabled {' +
                'cursor: not-allowed;' +
            '}';

        document.head.appendChild(styles);
    };

})();
