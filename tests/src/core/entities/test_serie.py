"""
Tests para las entidades Serie y Episode
"""
import pytest
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)

from src.core.entities.serie import Serie, Episode


class TestEpisodeEntity:
    """Tests para la entidad Episode"""
    
    def test_create_episode_basic(self):
        """Test de creación básica"""
        episode = Episode(
            id=1,
            serie_id=1,
            season=1,
            episode_number=1,
            title="Pilot"
        )
        
        assert episode.id == 1
        assert episode.serie_id == 1
        assert episode.season == 1
        assert episode.episode_number == 1
        assert episode.title == "Pilot"
    
    def test_display_title(self):
        """Test de título para mostrar"""
        episode = Episode(serie_id=1, season=1, episode_number=5, title="Test Episode")
        assert episode.display_title == "T01E05 - Test Episode"
    
    def test_size_mb(self):
        """Test de tamaño en MB"""
        episode = Episode(serie_id=1, season=1, episode_number=1, size=524288000)  # 500 MB
        assert episode.size_mb == 500.0
    
    def test_duration_formatted(self):
        """Test de duración formateada"""
        episode = Episode(serie_id=1, season=1, episode_number=1, duration=2700)  # 45 min
        assert episode.duration_formatted == "00:45:00"
    
    def test_to_dict(self):
        """Test de conversión a diccionario"""
        episode = Episode(
            id=1,
            serie_id=1,
            season=2,
            episode_number=3,
            title="Test"
        )
        
        data = episode.to_dict()
        
        assert data['id'] == 1
        assert data['season'] == 2
        assert data['episode_number'] == 3
        assert 'display_title' in data


class TestSerieEntity:
    """Tests para la entidad Serie"""
    
    def test_create_serie_basic(self):
        """Test de creación básica"""
        serie = Serie(
            id=1,
            name="Test Serie",
            year_start=2020
        )
        
        assert serie.id == 1
        assert serie.name == "Test Serie"
        assert serie.year_start == 2020
    
    def test_display_title(self):
        """Test de título para mostrar"""
        serie = Serie(name="Test Serie", year_start=2020)
        assert serie.display_title == "Test Serie (2020)"
        
        serie = Serie(name="Test Serie", year_start=2020, year_end=2023)
        assert serie.display_title == "Test Serie (2020-2023)"
    
    def test_total_episodes(self):
        """Test de total de episodios"""
        serie = Serie(
            name="Test",
            episodes=[
                Episode(serie_id=1, season=1, episode_number=1),
                Episode(serie_id=1, season=1, episode_number=2),
                Episode(serie_id=1, season=2, episode_number=1),
            ]
        )
        
        assert serie.total_episodes == 3
    
    def test_seasons(self):
        """Test de lista de temporadas"""
        serie = Serie(
            name="Test",
            episodes=[
                Episode(serie_id=1, season=1, episode_number=1),
                Episode(serie_id=1, season=1, episode_number=2),
                Episode(serie_id=1, season=2, episode_number=1),
                Episode(serie_id=1, season=3, episode_number=1),
            ]
        )
        
        assert serie.seasons == [1, 2, 3]
    
    def test_get_episodes_by_season(self):
        """Test de obtener episodios por temporada"""
        serie = Serie(
            name="Test",
            episodes=[
                Episode(serie_id=1, season=1, episode_number=1, title="Ep1"),
                Episode(serie_id=1, season=1, episode_number=2, title="Ep2"),
                Episode(serie_id=1, season=2, episode_number=1, title="Ep3"),
            ]
        )
        
        season1 = serie.get_episodes_by_season(1)
        assert len(season1) == 2
        assert season1[0].title == "Ep1"
        
        season2 = serie.get_episodes_by_season(2)
        assert len(season2) == 1
    
    def test_to_dict(self):
        """Test de conversión a diccionario"""
        serie = Serie(
            id=1,
            name="Test Serie",
            year_start=2020,
            year_end=2023,
            genre="Drama",
            episodes=[
                Episode(serie_id=1, season=1, episode_number=1)
            ]
        )
        
        data = serie.to_dict()
        
        assert data['id'] == 1
        assert data['name'] == "Test Serie"
        # Las temporadas se calculan dinámicamente
        assert data['total_episodes'] == 1
        assert len(data['episodes']) == 1
    
    def test_from_dict(self):
        """Test de creación desde diccionario"""
        data = {
            'id': 1,
            'name': 'Test Serie',
            'year_start': 2020,
            'episodes': [
                {'serie_id': 1, 'season': 1, 'episode_number': 1, 'title': 'Ep1'}
            ]
        }
        
        serie = Serie.from_dict(data)
        
        assert serie.id == 1
        assert serie.name == "Test Serie"
        assert len(serie.episodes) == 1


class TestSerieEdgeCases:
    """Tests para casos extremos"""
    
    def test_empty_serie(self):
        """Test con serie vacía"""
        serie = Serie(name="Test")
        assert serie.total_episodes == 0
        assert serie.seasons == []
    
    def test_serie_without_year(self):
        """Test sin año"""
        serie = Serie(name="Test Serie")
        assert serie.display_title == "Test Serie"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
