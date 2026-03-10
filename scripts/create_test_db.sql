-- Crear base de datos de test
CREATE DATABASE cine_app_db_test;

-- Conectar
\c cine_app_db_test;

-- Crear tabla app_users (misma estructura)
CREATE TABLE app_users (
    id SERIAL PRIMARY KEY,
    oauth_user_id INTEGER NOT NULL UNIQUE,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    avatar_url VARCHAR(500),
    bio TEXT,
    privacy_level VARCHAR(20) DEFAULT 'public',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP
);

-- Crear tabla user_preferences (si se necesita)
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    app_user_id INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE UNIQUE,
    preferred_genres JSONB,
    preferred_directors JSONB,
    preferred_actors JSONB,
    preferred_decades JSONB,
    avg_rating_given DECIMAL(3,2),
    total_movies_watched INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX idx_app_users_oauth ON app_users(oauth_user_id);
CREATE INDEX idx_app_users_username ON app_users(username);
CREATE INDEX idx_app_users_email ON app_users(email);
