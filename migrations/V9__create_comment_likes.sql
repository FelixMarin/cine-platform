-- V9: Crear tabla comment_likes
CREATE TABLE IF NOT EXISTS comment_likes (
    id SERIAL PRIMARY KEY,
    app_user_id INTEGER NOT NULL,
    comment_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_comment_likes_user FOREIGN KEY (app_user_id) 
        REFERENCES app_users(id) ON DELETE CASCADE,
    CONSTRAINT fk_comment_likes_comment FOREIGN KEY (comment_id) 
        REFERENCES movie_comments(id) ON DELETE CASCADE,
    CONSTRAINT uk_comment_likes_user_comment UNIQUE (app_user_id, comment_id)
);

CREATE INDEX idx_comment_likes_user ON comment_likes(app_user_id);
CREATE INDEX idx_comment_likes_comment ON comment_likes(comment_id);
