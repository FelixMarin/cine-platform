// Depende de thumbnailManager.js y categoryUtils.js

function createMovieCard(movie) {
    const card = document.createElement("div");
    card.classList.add("movie-card");

    const title = movie.name || movie.title || 'Sin título';

    // Si el thumbnail está pendiente, mostrar un placeholder con estilo
    if (movie.thumbnail_pending) {
        card.classList.add("thumbnail-pending");
    }

    // Si es una película nueva, añadir clase especial
    if (movie.is_new) {
        card.classList.add("new-movie");
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

    // Añadir badge de novedad si corresponde
    if (movie.is_new) {
        const badge = document.createElement('span');
        badge.className = 'new-badge';

        // Texto dinámico según antigüedad
        if (movie.days_ago === 0) {
            badge.textContent = 'HOY';
            badge.classList.add('hoy');
        } else if (movie.days_ago === 1) {
            badge.textContent = 'AYER';
            badge.classList.add('ayer');
        } else if (movie.days_ago <= 7) {
            badge.textContent = `HACE ${movie.days_ago} DÍAS`;
            badge.classList.add('semana');
        } else {
            badge.textContent = 'NUEVO';
        }

        card.appendChild(badge);

        // Añadir fecha exacta como tooltip
        if (movie.date_added) {
            card.setAttribute('title', `Añadida: ${movie.date_added}`);
        }

        // Añadir indicador visual de novedad
        const newIndicator = document.createElement('div');
        newIndicator.className = 'new-indicator';
        card.appendChild(newIndicator);
    }

    const playPath = movie.path || movie.id || movie.file;
    card.onclick = () => window.playMovie(playPath);

    return card;
}

// Función para series (sin badge de novedad)
async function createSerieCard(episodio) {
    const card = document.createElement("div");
    card.classList.add("movie-card");

    const title = episodio.name || episodio.title || 'Sin título';

    // Determinar la URL del thumbnail
    let thumbnailUrl;
    if (episodio.thumbnail) {
        thumbnailUrl = episodio.thumbnail;
    } else {
        thumbnailUrl = await window.getThumbnailUrl(episodio);
    }

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

    const playPath = episodio.path || episodio.id || episodio.file;
    card.onclick = () => window.playMovie(playPath);

    return card;
}

// También necesitas añadir el CSS para los nuevos elementos
// Esto se puede añadir en un archivo CSS separado, pero lo incluyo aquí como referencia
const style = document.createElement('style');
style.textContent = `
    /* ===== NOVEDADES ===== */
    .movie-card {
        position: relative;
        overflow: visible;
    }

    .new-badge {
        position: absolute;
        top: -8px;
        right: -8px;
        background: linear-gradient(135deg, var(--accent-color), #ff4d4d);
        color: white;
        font-size: 0.7rem;
        font-weight: bold;
        padding: 4px 8px;
        border-radius: 20px;
        z-index: 10;
        box-shadow: 0 4px 10px rgba(229, 9, 20, 0.5);
        animation: pulse 2s infinite;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        white-space: nowrap;
    }

    .new-badge.hoy {
        background: linear-gradient(135deg, #ff6b6b, var(--accent-color));
        animation: intense-pulse 1s infinite;
        font-weight: 800;
    }

    .new-badge.ayer {
        background: linear-gradient(135deg, #ff8a8a, var(--accent-color));
        animation: pulse 1.5s infinite;
    }

    .new-badge.semana {
        background: linear-gradient(135deg, var(--accent-color), #ffaa00);
        animation: soft-pulse 3s infinite;
    }

    .movie-card.new-movie {
        border: 2px solid var(--accent-color);
        box-shadow: 0 0 15px rgba(229, 9, 20, 0.3);
        transition: all 0.3s ease;
    }

    .movie-card.new-movie:hover {
        transform: translateY(-8px);
        box-shadow: 0 0 25px rgba(229, 9, 20, 0.5);
        border-color: var(--accent-hover);
    }

    .new-indicator {
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(to bottom, var(--accent-color), #ff8a8a);
        border-radius: 4px 0 0 4px;
        opacity: 0.8;
    }

    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 4px 10px rgba(229, 9, 20, 0.5); }
        50% { transform: scale(1.05); box-shadow: 0 4px 15px rgba(229, 9, 20, 0.7); }
        100% { transform: scale(1); box-shadow: 0 4px 10px rgba(229, 9, 20, 0.5); }
    }

    @keyframes intense-pulse {
        0% { transform: scale(1); box-shadow: 0 4px 15px rgba(229, 9, 20, 0.7); }
        50% { transform: scale(1.1); box-shadow: 0 4px 25px rgba(229, 9, 20, 0.9); }
        100% { transform: scale(1); box-shadow: 0 4px 15px rgba(229, 9, 20, 0.7); }
    }

    @keyframes soft-pulse {
        0% { transform: scale(1); opacity: 0.9; }
        50% { transform: scale(1.03); opacity: 1; }
        100% { transform: scale(1); opacity: 0.9; }
    }

    /* Tooltip personalizado */
    .movie-card[title] {
        position: relative;
        cursor: pointer;
    }

    .movie-card[title]:hover::after {
        content: attr(title);
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.7rem;
        white-space: nowrap;
        z-index: 20;
        pointer-events: none;
        margin-bottom: 5px;
    }
`;

// Añadir el estilo al documento si no existe
if (!document.getElementById('movie-card-styles')) {
    style.id = 'movie-card-styles';
    document.head.appendChild(style);
}

window.createMovieCard = createMovieCard;
window.createSerieCard = createSerieCard;