-- V11: Crear tabla notifications
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    app_user_id INTEGER NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    actor_user_id INTEGER,
    movie_id INTEGER,
    comment_id INTEGER,
    title VARCHAR(255),
    message TEXT,
    deep_link VARCHAR(500),
    is_read BOOLEAN DEFAULT false,
    is_clicked BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,
    
    CONSTRAINT fk_notifications_user FOREIGN KEY (app_user_id) 
        REFERENCES app_users(id) ON DELETE CASCADE,
    CONSTRAINT fk_notifications_actor FOREIGN KEY (actor_user_id) 
        REFERENCES app_users(id) ON DELETE SET NULL,
    CONSTRAINT fk_notifications_movie FOREIGN KEY (movie_id) 
        REFERENCES movie_metadata(id) ON DELETE CASCADE,
    CONSTRAINT fk_notifications_comment FOREIGN KEY (comment_id) 
        REFERENCES movie_comments(id) ON DELETE CASCADE
);

CREATE INDEX idx_notifications_user ON notifications(app_user_id, is_read);
CREATE INDEX idx_notifications_created ON notifications(created_at DESC);
