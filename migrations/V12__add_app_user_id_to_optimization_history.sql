-- V12: Añadir columna app_user_id a optimization_history
-- Esta columna permite vincular cada optimización con el usuario que la inició

ALTER TABLE optimization_history 
ADD COLUMN IF NOT EXISTS app_user_id INTEGER REFERENCES app_users(id);

CREATE INDEX IF NOT EXISTS idx_optimization_history_app_user 
ON optimization_history(app_user_id);
