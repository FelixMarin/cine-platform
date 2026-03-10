-- V10: Crear tabla user_follows (auto-referencia)
CREATE TABLE IF NOT EXISTS user_follows (
    id SERIAL PRIMARY KEY,
    follower_id INTEGER NOT NULL,
    followed_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_follows_follower FOREIGN KEY (follower_id) 
        REFERENCES app_users(id) ON DELETE CASCADE,
    CONSTRAINT fk_follows_followed FOREIGN KEY (followed_id) 
        REFERENCES app_users(id) ON DELETE CASCADE,
    CONSTRAINT uk_follows UNIQUE (follower_id, followed_id),
    CONSTRAINT chk_follows_no_self CHECK (follower_id != followed_id)
);

CREATE INDEX idx_follows_follower ON user_follows(follower_id);
CREATE INDEX idx_follows_followed ON user_follows(followed_id);
