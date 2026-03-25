-- Script para crear la tabla movie_likes
-- Esta tabla almacena los likes de los usuarios en películas

-- Crear la tabla movie_likes si no existe
CREATE TABLE IF NOT EXISTS movie_likes (
    id SERIAL PRIMARY KEY,
    app_user_id INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    local_content_id INTEGER NOT NULL REFERENCES local_content(id) ON DELETE CASCADE,
    tmdb_id INTEGER,
    movie_title VARCHAR(255) NOT NULL,
    like_type VARCHAR(20) DEFAULT 'like',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear índice único para evitar votos duplicados (un like por usuario por película)
CREATE UNIQUE INDEX IF NOT EXISTS uk_likes_user_content 
ON movie_likes(app_user_id, local_content_id);

-- Crear índice para buscar likes por usuario
CREATE INDEX IF NOT EXISTS idx_likes_user_id 
ON movie_likes(app_user_id);

-- Crear índice para buscar likes por contenido
CREATE INDEX IF NOT EXISTS idx_likes_content_id 
ON movie_likes(local_content_id);

-- Comentario para la tabla
COMMENT ON TABLE movie_likes IS 'Almacena los likes de usuarios en películas';
COMMENT ON COLUMN movie_likes.app_user_id IS 'ID del usuario que dio like';
COMMENT ON COLUMN movie_likes.local_content_id IS 'ID del contenido local (película)';
COMMENT ON COLUMN movie_likes.tmdb_id IS 'ID de TMDB (opcional)';
COMMENT ON COLUMN movie_likes.movie_title IS 'Título de la película (denormalizado)';
COMMENT ON COLUMN movie_likes.like_type IS 'Tipo de like (por defecto like)';
COMMENT ON COLUMN movie_likes.created_at IS 'Fecha de creación del like';
