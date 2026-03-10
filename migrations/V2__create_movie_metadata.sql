-- V2: Crear tabla movie_metadata (caché de TMDB/OMDB)
CREATE TABLE IF NOT EXISTS movie_metadata (
    id SERIAL PRIMARY KEY,
    tmdb_id INTEGER UNIQUE,
    imdb_id VARCHAR(20) UNIQUE,
    title VARCHAR(255) NOT NULL,
    original_title VARCHAR(255),
    release_year INTEGER,
    release_date DATE,
    runtime INTEGER,
    genres JSONB,
    directors JSONB,
    movie_cast JSONB,
    writers JSONB,
    plot TEXT,
    poster_url VARCHAR(500),
    backdrop_url VARCHAR(500),
    imdb_rating DECIMAL(3,1),
    imdb_votes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metadata_tmdb ON movie_metadata(tmdb_id);
CREATE INDEX idx_metadata_imdb ON movie_metadata(imdb_id);
CREATE INDEX idx_metadata_title ON movie_metadata(title);
