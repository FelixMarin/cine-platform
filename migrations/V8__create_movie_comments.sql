-- V8: Crear tabla movie_comments (jerárquica)
CREATE TABLE IF NOT EXISTS movie_comments (
    id SERIAL PRIMARY KEY,
    app_user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    tmdb_id INTEGER,
    movie_title VARCHAR(255) NOT NULL,
    comment_text TEXT NOT NULL,
    parent_comment_id INTEGER,
    is_spoiler BOOLEAN DEFAULT false,
    is_edited BOOLEAN DEFAULT false,
    likes_count INTEGER DEFAULT 0,
    replies_count INTEGER DEFAULT 0,
    is_reported BOOLEAN DEFAULT false,
    is_hidden BOOLEAN DEFAULT false,
    hidden_reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_comments_user FOREIGN KEY (app_user_id) 
        REFERENCES app_users(id) ON DELETE CASCADE,
    CONSTRAINT fk_comments_movie FOREIGN KEY (movie_id) 
        REFERENCES movie_metadata(id) ON DELETE CASCADE,
    CONSTRAINT fk_comments_parent FOREIGN KEY (parent_comment_id) 
        REFERENCES movie_comments(id) ON DELETE CASCADE
);

CREATE INDEX idx_comments_user ON movie_comments(app_user_id);
CREATE INDEX idx_comments_movie ON movie_comments(movie_id);
CREATE INDEX idx_comments_parent ON movie_comments(parent_comment_id);
CREATE INDEX idx_comments_created ON movie_comments(created_at DESC);
