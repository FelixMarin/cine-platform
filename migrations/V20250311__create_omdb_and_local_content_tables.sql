-- V20250311: Crear tablas omdb_entries y local_content para catálogo de películas/series
-- Tabla con todos los campos de la API de OMDB

CREATE TABLE IF NOT EXISTS omdb_entries (
    id SERIAL PRIMARY KEY,
    imdb_id VARCHAR(20) UNIQUE,
    title VARCHAR(500),
    year VARCHAR(10),
    rated VARCHAR(10),
    released VARCHAR(50),
    runtime VARCHAR(50),
    genre VARCHAR(500),
    director VARCHAR(500),
    writer VARCHAR(1000),
    actors VARCHAR(2000),
    plot TEXT,
    language VARCHAR(500),
    country VARCHAR(200),
    awards VARCHAR(500),
    poster_url VARCHAR(1000),
    poster_image BYTEA,
    metascore INTEGER,
    imdb_rating DECIMAL(3,1),
    imdb_votes VARCHAR(20),
    type VARCHAR(20),
    box_office VARCHAR(50),
    production VARCHAR(500),
    website VARCHAR(500),
    dvd_release VARCHAR(50),
    total_seasons INTEGER,
    season INTEGER,
    episode INTEGER,
    series_id VARCHAR(20),
    ratings JSONB,
    full_response JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE omdb_entries IS 'Almacena datos de películas y series obtenidos de la API OMDB';
COMMENT ON COLUMN omdb_entries.imdb_id IS 'Identificador único de IMDB (ej: tt1234567)';
COMMENT ON COLUMN omdb_entries.title IS 'Título de la película o serie';
COMMENT ON COLUMN omdb_entries.type IS 'Tipo de contenido: movie, series, episode, game';
COMMENT ON COLUMN omdb_entries.ratings IS 'Ratings de diferentes fuentes (Rotten Tomatoes, Metacritic, etc.)';
COMMENT ON COLUMN omdb_entries.full_response IS 'Respuesta completa de la API OMDB para referencia';

-- Tabla de contenido local con archivos asociados

CREATE TABLE IF NOT EXISTS local_content (
    id SERIAL PRIMARY KEY,
    imdb_id VARCHAR(20) REFERENCES omdb_entries(imdb_id),
    title VARCHAR(500),
    year VARCHAR(10),
    rated VARCHAR(10),
    released VARCHAR(50),
    runtime VARCHAR(50),
    genre VARCHAR(500),
    director VARCHAR(500),
    writer VARCHAR(1000),
    actors VARCHAR(2000),
    plot TEXT,
    language VARCHAR(500),
    country VARCHAR(200),
    awards VARCHAR(500),
    poster_url VARCHAR(1000),
    poster_image BYTEA,
    metascore INTEGER,
    imdb_rating DECIMAL(3,1),
    imdb_votes VARCHAR(20),
    type VARCHAR(20),
    box_office VARCHAR(50),
    production VARCHAR(500),
    website VARCHAR(500),
    dvd_release VARCHAR(50),
    total_seasons INTEGER,
    season INTEGER,
    episode INTEGER,
    series_id VARCHAR(20),
    ratings JSONB,
    full_response JSONB,
    file_path VARCHAR(1000),
    file_size BIGINT,
    duration VARCHAR(20),
    resolution VARCHAR(20),
    codec VARCHAR(50),
    quality VARCHAR(50),
    format VARCHAR(20),
    is_optimized BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE local_content IS 'Almacena contenido local (archivos de películas/series) con metadatos OMDB';
COMMENT ON COLUMN local_content.file_path IS 'Ruta al archivo de video en el sistema de archivos';
COMMENT ON COLUMN local_content.file_size IS 'Tamaño del archivo en bytes';
COMMENT ON COLUMN local_content.duration IS 'Duración del video (ej: 120 min)';
COMMENT ON COLUMN local_content.resolution IS 'Resolución de video (ej: 1920x1080, 4K)';
COMMENT ON COLUMN local_content.codec IS 'Códec de video (ej: x264, x265, VP9)';
COMMENT ON COLUMN local_content.quality IS 'Calidad de video (ej: BluRay, WebDL, HDTV)';
COMMENT ON COLUMN local_content.format IS 'Formato del archivo (mkv, mp4, avi)';
COMMENT ON COLUMN local_content.is_optimized IS 'Indica si el archivo ha sido optimizado para streaming';

-- Índices para omdb_entries

CREATE INDEX IF NOT EXISTS idx_omdb_entries_imdb_id ON omdb_entries(imdb_id);
CREATE INDEX IF NOT EXISTS idx_omdb_entries_title ON omdb_entries(title);
CREATE INDEX IF NOT EXISTS idx_omdb_entries_type ON omdb_entries(type);
CREATE INDEX IF NOT EXISTS idx_omdb_entries_year ON omdb_entries(year);
CREATE INDEX IF NOT EXISTS idx_omdb_entries_genre ON omdb_entries(genre);

-- Índices para local_content

CREATE INDEX IF NOT EXISTS idx_local_content_imdb_id ON local_content(imdb_id);
CREATE INDEX IF NOT EXISTS idx_local_content_title ON local_content(title);
CREATE INDEX IF NOT EXISTS idx_local_content_type ON local_content(type);
CREATE INDEX IF NOT EXISTS idx_local_content_file_path ON local_content(file_path);
