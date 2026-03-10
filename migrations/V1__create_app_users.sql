-- V1: Crear tabla app_users (perfiles de usuario)
CREATE TABLE IF NOT EXISTS app_users (
    id SERIAL PRIMARY KEY,
    oauth_user_id INTEGER NOT NULL UNIQUE,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(100),
    avatar_url VARCHAR(500),
    bio TEXT,
    privacy_level VARCHAR(20) DEFAULT 'public',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP
);

CREATE INDEX idx_app_users_oauth ON app_users(oauth_user_id);
CREATE INDEX idx_app_users_username ON app_users(username);
CREATE INDEX idx_app_users_email ON app_users(email);
