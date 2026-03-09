import pytest
import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock
from src.adapters.outgoing.services.optimizer.postprocess import (
    PostProcessor,
    CatalogUpdater,
    process_completed_optimization,
)


class TestPostProcessor:
    @pytest.fixture
    def temp_dirs(self):
        temp_root = tempfile.mkdtemp()
        movies_folder = os.path.join(temp_root, "movies")
        upload_folder = os.path.join(temp_root, "uploads")
        os.makedirs(movies_folder)
        os.makedirs(upload_folder)

        with patch(
            "src.adapters.outgoing.services.optimizer.postprocess.settings"
        ) as mock_settings:
            mock_settings.MOVIES_FOLDER = movies_folder
            mock_settings.UPLOAD_FOLDER = upload_folder
            processor = PostProcessor()
            processor.movies_folder = movies_folder
            processor.upload_folder = upload_folder

        yield processor, movies_folder, upload_folder

        shutil.rmtree(temp_root, ignore_errors=True)

    def test_get_final_path_action(self, temp_dirs):
        processor, movies_folder, _ = temp_dirs
        path = processor.get_final_path("Acción", "movie.mkv")
        assert "action" in path
        assert path.endswith("movie.mkv")

    def test_get_final_path_animation(self, temp_dirs):
        processor, movies_folder, _ = temp_dirs
        path = processor.get_final_path("Animación", "movie.mkv")
        assert "animation" in path

    def test_get_final_path_unknown_category(self, temp_dirs):
        processor, movies_folder, _ = temp_dirs
        path = processor.get_final_path("UnknownCategory", "movie.mkv")
        assert "other" in path

    def test_get_final_path_creates_directory(self, temp_dirs):
        processor, movies_folder, _ = temp_dirs
        path = processor.get_final_path("Comedia", "movie.mkv")
        assert os.path.exists(os.path.dirname(path))

    def test_move_to_final_success(self, temp_dirs):
        processor, movies_folder, upload_folder = temp_dirs

        source_file = os.path.join(upload_folder, "source.mkv")
        with open(source_file, "w") as f:
            f.write("test content")

        result = processor.move_to_final(source_file, "Drama", "new_name.mkv")

        assert result["success"] is True
        assert result["category"] == "Drama"
        assert "drama" in result["destination"]
        assert os.path.exists(result["destination"])
        assert not os.path.exists(source_file)

    def test_move_to_final_file_not_found(self, temp_dirs):
        processor, movies_folder, upload_folder = temp_dirs

        with pytest.raises(FileNotFoundError):
            processor.move_to_final("/nonexistent/file.mkv", "Drama", "movie.mkv")

    def test_get_unique_filename_new(self, temp_dirs):
        processor, movies_folder, _ = temp_dirs
        filename = processor._get_unique_filename("Drama", "movie.mkv")
        assert filename == "movie.mkv"

    def test_get_unique_filename_existing(self, temp_dirs):
        processor, movies_folder, _ = temp_dirs

        target_dir = os.path.join(movies_folder, "mkv", "drama")
        os.makedirs(target_dir)
        existing_file = os.path.join(target_dir, "movie.mkv")
        with open(existing_file, "w") as f:
            f.write("existing")

        filename = processor._get_unique_filename("Drama", "movie.mkv")
        assert filename == "movie_1.mkv"

    def test_cleanup_temp_files_main_file(self, temp_dirs):
        processor, movies_folder, upload_folder = temp_dirs

        temp_file = os.path.join(upload_folder, "temp.mkv")
        with open(temp_file, "w") as f:
            f.write("temp")

        result = processor.cleanup_temp_files(temp_file)

        assert len(result["cleaned"]) == 1
        assert not os.path.exists(temp_file)

    def test_cleanup_temp_files_related_files(self, temp_dirs):
        processor, movies_folder, upload_folder = temp_dirs

        main_file = os.path.join(upload_folder, "main.mkv")
        related_file = os.path.join(upload_folder, "related.srt")

        with open(main_file, "w") as f:
            f.write("main")
        with open(related_file, "w") as f:
            f.write("related")

        result = processor.cleanup_temp_files(main_file, related_files=[related_file])

        assert len(result["cleaned"]) == 2

    def test_cleanup_temp_files_non_temp_file(self, temp_dirs):
        processor, movies_folder, upload_folder = temp_dirs

        non_temp = os.path.join(movies_folder, "movie.mkv")
        with open(non_temp, "w") as f:
            f.write("movie")

        result = processor.cleanup_temp_files(non_temp)
        assert len(result["cleaned"]) == 0
        assert os.path.exists(non_temp)


class TestCatalogUpdater:
    def test_refresh_category(self):
        with patch(
            "src.adapters.outgoing.services.optimizer.postprocess.settings"
        ) as mock_settings:
            mock_settings.MOVIES_FOLDER = "/tmp/movies"
            updater = CatalogUpdater()
            updater.refresh_category("Drama")

    def test_register_movie(self):
        with patch(
            "src.adapters.outgoing.services.optimizer.postprocess.settings"
        ) as mock_settings:
            mock_settings.MOVIES_FOLDER = "/tmp/movies"
            updater = CatalogUpdater()

            result = updater.register_movie("/tmp/movies/drama/movie.mkv", "Drama")

            assert result["success"] is True
            assert "movie.mkv" in result["filename"]
            assert result["category"] == "Drama"


class TestProcessCompletedOptimization:
    def test_process_completed_optimization_success(self):
        with patch(
            "src.adapters.outgoing.services.optimizer.postprocess.settings"
        ) as mock_settings:
            mock_settings.MOVIES_FOLDER = tempfile.mkdtemp()
            mock_settings.UPLOAD_FOLDER = tempfile.mkdtemp()

            temp_dir = tempfile.mkdtemp()
            output_path = os.path.join(temp_dir, "output.mkv")
            with open(output_path, "w") as f:
                f.write("test content")

            job_data = {
                "output_path": output_path,
                "category": "Drama",
                "original_filename": "movie.mkv",
            }

            result = process_completed_optimization("job-123", job_data)

            assert result["moved"] is True
            assert result["catalog_updated"] is True
            assert result["cleaned"] is True
            assert len(result["errors"]) == 0

            shutil.rmtree(temp_dir, ignore_errors=True)
            shutil.rmtree(mock_settings.MOVIES_FOLDER, ignore_errors=True)
            shutil.rmtree(mock_settings.UPLOAD_FOLDER, ignore_errors=True)

    def test_process_completed_optimization_no_output(self):
        job_data = {
            "output_path": "/nonexistent/output.mkv",
            "category": "Drama",
            "original_filename": "movie.mkv",
        }

        result = process_completed_optimization("job-123", job_data)

        assert result["moved"] is False
        assert len(result["errors"]) > 0

    def test_process_completed_optimization_no_original_filename(self):
        with patch(
            "src.adapters.outgoing.services.optimizer.postprocess.settings"
        ) as mock_settings:
            mock_settings.MOVIES_FOLDER = tempfile.mkdtemp()
            mock_settings.UPLOAD_FOLDER = tempfile.mkdtemp()

            temp_dir = tempfile.mkdtemp()
            output_path = os.path.join(temp_dir, "output.mkv")
            with open(output_path, "w") as f:
                f.write("test content")

            job_data = {"output_path": output_path, "category": "Drama"}

            result = process_completed_optimization("job-123", job_data)

            assert result["moved"] is True

            shutil.rmtree(temp_dir, ignore_errors=True)
            shutil.rmtree(mock_settings.MOVIES_FOLDER, ignore_errors=True)
            shutil.rmtree(mock_settings.UPLOAD_FOLDER, ignore_errors=True)


class TestCategoryPaths:
    def test_category_paths_all_categories(self):
        expected = {
            "Acción": "action",
            "Animación": "animation",
            "Aventura": "adventure",
            "Ciencia Ficción": "sci-fi",
            "Comedia": "comedy",
            "Documental": "documentary",
            "Drama": "drama",
            "Familia": "family",
            "Fantasía": "fantasy",
            "Historia": "history",
            "Música": "music",
            "Misterio": "mystery",
            "Romance": "romance",
            "Suspense": "thriller",
            "Terror": "horror",
            "Western": "western",
        }
        assert PostProcessor.CATEGORY_PATHS == expected
