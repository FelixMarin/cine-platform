// Cache para thumbnails
const thumbnailCache = new Map();

// Exportar para uso en otros módulos
window.thumbnailCache = thumbnailCache;

// Función para verificar soporte de WebP
function checkWebPSupport() {
    return new Promise(resolve => {
        const webP = new Image();
        webP.onload = webP.onerror = function () {
            resolve(webP.height === 2);
        };
        webP.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';
    });
}

window.checkWebPSupport = checkWebPSupport;