// Depende de cache.js

async function getThumbnailUrl(movie) {
    const name = movie.name || movie.title || '';
    const cleanName = name.trim().replace(/\s+/g, ' ');
    const cacheKey = cleanName;

    // Si ya está en caché, devolverlo
    if (window.thumbnailCache.has(cacheKey)) {
        return window.thumbnailCache.get(cacheKey);
    }

    // Si ya tiene thumbnail en los datos, usarlo
    if (movie.thumbnail) {
        window.thumbnailCache.set(cacheKey, movie.thumbnail);
        return movie.thumbnail;
    }

    const encodedName = encodeURIComponent(cleanName);

    // Verificar soporte WebP (una sola vez)
    if (!window.supportsWebP) {
        window.supportsWebP = await checkWebPSupport();
    }

    let thumbnailUrl;

    // Si soporta WebP, intentar obtener versión WebP
    if (window.supportsWebP) {
        try {
            const response = await fetch(`/thumbnails/detect/${encodedName}-optimized.jpg`);
            const data = await response.json();

            if (data.has_webp) {
                thumbnailUrl = data.webp_url;
            } else if (data.has_jpg) {
                thumbnailUrl = data.jpg_url;
            } else {
                thumbnailUrl = `/thumbnails/${encodedName}-optimized.jpg`;
            }
        } catch (error) {
            console.log('Error detectando formato, usando JPG');
            thumbnailUrl = `/thumbnails/${encodedName}-optimized.jpg`;
        }
    } else {
        thumbnailUrl = `/thumbnails/${encodedName}-optimized.jpg`;
    }

    // Guardar en caché
    window.thumbnailCache.set(cacheKey, thumbnailUrl);
    return thumbnailUrl;
}

// Verificar estado de thumbnails cada 5 segundos
setInterval(() => {
    fetch('/api/thumbnail-status')
        .then(r => r.json())
        .then(data => {
            const progressDiv = document.getElementById('thumbnail-progress');
            const countSpan = document.getElementById('thumbnail-count');

            if (data.queue_size > 0) {
                countSpan.textContent = data.queue_size;
                progressDiv.style.display = 'block';
            } else {
                progressDiv.style.display = 'none';
            }
        })
        .catch(err => console.log('Error checking thumbnail status'));
}, 5000);

window.getThumbnailUrl = getThumbnailUrl;