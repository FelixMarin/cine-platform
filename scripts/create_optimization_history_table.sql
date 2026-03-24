-- Script para crear la tabla optimization_history si no existe
-- Este script debe ejecutarse en la base de datos del catálogo

CREATE TABLE IF NOT EXISTS optimization_history (
    id SERIAL PRIMARY KEY,
    process_id VARCHAR(36) UNIQUE NOT NULL,
    torrent_id INTEGER,
    torrent_name VARCHAR(500) NOT NULL,
    movie_name VARCHAR(255),  -- Añadido este campo
    category VARCHAR(100) NOT NULL,
    input_file VARCHAR(500),
    output_file VARCHAR(500),
    output_filename VARCHAR(500),
    
    -- Fechas - nombres correctos
    torrent_download_start TIMESTAMP,
    torrent_download_end TIMESTAMP,
    optimization_start TIMESTAMP NOT NULL,
    optimization_end TIMESTAMP,
    
    -- Duración en segundos
    download_duration_seconds INTEGER,
    optimization_duration_seconds INTEGER,
    
    -- Resultado
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    
    -- Tamaños y compresión
    file_size_bytes BIGINT,
    original_size_bytes BIGINT,
    compression_ratio NUMERIC(5, 2),
    
    -- Tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Usuario
    app_user_id INTEGER NOT NULL  -- Añadido NOT NULL
);

-- Crear índices si no existen
CREATE INDEX IF NOT EXISTS idx_optimization_history_process_id ON optimization_history(process_id);
CREATE INDEX IF NOT EXISTS idx_optimization_history_status ON optimization_history(status);
CREATE INDEX IF NOT EXISTS idx_optimization_history_created_at ON optimization_history(created_at);

-- Verificar que la tabla fue creada
SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = 'optimization_history';
