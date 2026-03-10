-- V6: Crear tabla user_watchlist (relación N:N)
CREATE TABLE IF NOT EXISTS user_watchlist (
    id SERIAL PRIMARY KEY,
    app_user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    tmdb_id INTEGER,
    movie_title VARCHAR(255) NOT NULL,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    priority INTEGER DEFAULT 5,
    notes TEXT,
    reminder_date DATE,
    reminder_sent BOOLEAN DEFAULT false,
    
    CONSTRAINT fk_watchlist_user FOREIGN KEY (app_user_id) 
        REFERENCES app_users(id) ON DELETE CASCADE,
    CONSTRAINT fk_watchlist_movie FOREIGN KEY (movie_id) 
        REFERENCES movie_metadata(id) ON DELETE CASCADE,
    CONSTRAINT uk_watchlist_user_movie UNIQUE (app_user_id, movie_id)
);

CREATE INDEX idx_watchlist_user ON user_watchlist(app_user_id);
CREATE INDEX idx_watchlist_movie ON user_watchlist(movie_id);
