-- V5: Crear tabla user_view_history
CREATE TABLE IF NOT EXISTS user_view_history (
    id SERIAL PRIMARY KEY,
    app_user_id INTEGER NOT NULL,
    movie_id INTEGER,
    tmdb_id INTEGER,
    movie_title VARCHAR(255) NOT NULL,
    watched_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    watch_duration INTEGER,
    completed BOOLEAN DEFAULT false,
    device_type VARCHAR(50),
    user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 10),
    user_review TEXT,
    favorite BOOLEAN DEFAULT false,
    source VARCHAR(50),
    session_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_view_user FOREIGN KEY (app_user_id) 
        REFERENCES app_users(id) ON DELETE CASCADE,
    CONSTRAINT fk_view_movie FOREIGN KEY (movie_id) 
        REFERENCES movie_metadata(id) ON DELETE SET NULL
);

CREATE INDEX idx_view_user ON user_view_history(app_user_id);
CREATE INDEX idx_view_movie ON user_view_history(movie_id);
CREATE INDEX idx_view_date ON user_view_history(watched_date DESC);
