// Depende de thumbnailManager.js y categoryUtils.js

function createMovieCard(movie) {
    const card = document.createElement("div");
    card.classList.add("movie-card");

    const title = movie.name || movie.title || 'Sin título';

    // Si el thumbnail está pendiente, mostrar un placeholder con estilo
    if (movie.thumbnail_pending) {
        card.classList.add("thumbnail-pending");
    }

    const thumbnailUrl = movie.thumbnail || '/static/images/default.jpg';

    const img = document.createElement('img');
    img.className = 'movie-thumb';
    img.alt = title;
    img.src = thumbnailUrl;
    img.onerror = function () {
        this.src = '/static/images/default.jpg';
        this.onerror = null;
    };

    const titleDiv = document.createElement('div');
    titleDiv.className = 'movie-title';
    titleDiv.textContent = title;

    card.appendChild(img);
    card.appendChild(titleDiv);

    const playPath = movie.path || movie.id || movie.file;
    card.onclick = () => window.playMovie(playPath);

    return card;
}

// Nueva función asíncrona para crear tarjetas de series
async function createSerieCard(episodio) {
    const card = document.createElement("div");
    card.classList.add("movie-card");

    const title = episodio.name || episodio.title || 'Sin título';

    // Determinar la URL del thumbnail
    let thumbnailUrl;
    if (episodio.thumbnail) {
        thumbnailUrl = episodio.thumbnail;
    } else {
        // Intentar usar getThumbnailUrl para series también
        thumbnailUrl = await window.getThumbnailUrl(episodio);
    }

    // Crear imagen
    const img = document.createElement('img');
    img.className = 'movie-thumb';
    img.alt = title;
    img.src = thumbnailUrl;
    img.onerror = function () {
        console.log('Error en serie, usando default:', this.src);
        this.src = '/static/images/default.jpg';
        this.onerror = null;
    };

    const titleDiv = document.createElement('div');
    titleDiv.className = 'movie-title';
    titleDiv.textContent = title;

    card.appendChild(img);
    card.appendChild(titleDiv);

    const playPath = episodio.path || episodio.id || episodio.file;
    card.onclick = () => window.playMovie(playPath);

    return card;
}

window.createMovieCard = createMovieCard;
window.createSerieCard = createSerieCard;