"""
Jackett - Servicio de indexación de torrents

Este módulo proporciona un cliente asíncrono para buscar torrents usando Jackett.
"""
from src.adapters.outgoing.services.jackett.client import JackettClient, JackettSearchResult, JackettError

__all__ = ['JackettClient', 'JackettSearchResult', 'JackettError']
