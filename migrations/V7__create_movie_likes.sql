-- V7: Crear tabla movie_likes
CREATE TABLE IF NOT EXISTS movie_likes (
    id SERIAL PRIMARY KEY,
    app_user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    tmdb_id INTEGER,
    movie_title VARCHAR(255) NOT NULL,
    like_type VARCHAR(20) DEFAULT 'like',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_likes_user FOREIGN KEY (app_user_id) 
        REFERENCES app_users(id) ON DELETE CASCADE,
    CONSTRAINT fk_likes_movie FOREIGN KEY (movie_id) 
        REFERENCES movie_metadata(id) ON DELETE CASCADE,
    CONSTRAINT uk_likes_user_movie UNIQUE (app_user_id, movie_id)
);

CREATE INDEX idx_likes_user ON movie_likes(app_user_id);
CREATE INDEX idx_likes_movie ON movie_likes(movie_id);
