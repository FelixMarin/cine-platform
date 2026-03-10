-- V3: Crear tabla user_preferences (relación 1:1 con app_users)
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    app_user_id INTEGER NOT NULL UNIQUE,
    preferred_genres JSONB,
    preferred_directors JSONB,
    preferred_actors JSONB,
    preferred_decades JSONB,
    avg_rating_given DECIMAL(3,2),
    total_movies_watched INTEGER DEFAULT 0,
    total_movies_optimized INTEGER DEFAULT 0,
    min_imdb_rating DECIMAL(3,1) DEFAULT 6.0,
    enable_recommendations BOOLEAN DEFAULT true,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_preferences_user FOREIGN KEY (app_user_id) 
        REFERENCES app_users(id) ON DELETE CASCADE
);

CREATE INDEX idx_preferences_user ON user_preferences(app_user_id);
