-- V4: Crear tabla optimization_history
CREATE TABLE IF NOT EXISTS optimization_history (
    id SERIAL PRIMARY KEY,
    app_user_id INTEGER NOT NULL,
    movie_id INTEGER,
    movie_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    download_started TIMESTAMP,
    download_completed TIMESTAMP,
    optimization_started TIMESTAMP,
    optimization_completed TIMESTAMP,
    original_size_bytes BIGINT,
    optimized_size_bytes BIGINT,
    compression_ratio DECIMAL(5,2),
    status VARCHAR(50),
    error_message TEXT,
    torrent_id INTEGER,
    process_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_history_user FOREIGN KEY (app_user_id) 
        REFERENCES app_users(id) ON DELETE CASCADE,
    CONSTRAINT fk_history_movie FOREIGN KEY (movie_id) 
        REFERENCES movie_metadata(id) ON DELETE SET NULL
);

CREATE INDEX idx_history_user ON optimization_history(app_user_id);
CREATE INDEX idx_history_movie ON optimization_history(movie_id);
CREATE INDEX idx_history_status ON optimization_history(status);
