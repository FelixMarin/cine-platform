-- V18__update_unique_key_omdb_entries.sql

-- 1. Verificar duplicados de title + year (ejecutar manualmente)
-- SELECT title, year, COUNT(*) 
-- FROM public.omdb_entries 
-- GROUP BY title, year 
-- HAVING COUNT(*) > 1;

-- 2. Eliminar la clave foránea
ALTER TABLE public.local_content 
DROP CONSTRAINT IF EXISTS local_content_imdb_id_fkey;

-- 3. Añadir la nueva clave única compuesta por title y year
-- (mantenemos también la única de imdb_id para no romper la integridad)
ALTER TABLE public.omdb_entries 
ADD CONSTRAINT omdb_entries_title_year_key 
UNIQUE (title, year);

-- 4. Recrear la clave foránea (ahora referenciando la columna imdb_id que sigue siendo única)
ALTER TABLE public.local_content 
ADD CONSTRAINT local_content_imdb_id_fkey 
FOREIGN KEY (imdb_id) 
REFERENCES public.omdb_entries(imdb_id);

-- 5. Crear índice para la nueva restricción compuesta
CREATE INDEX IF NOT EXISTS idx_omdb_entries_title_year 
ON public.omdb_entries USING btree (title, year);