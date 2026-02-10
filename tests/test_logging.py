import unittest
import logging
import sys
import os
from unittest.mock import patch

# Asegurar que el proyecto está en el PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.logging.logging_config import setup_logging


class TestLogging(unittest.TestCase):

    @patch('modules.logging.logging_config.Path.mkdir')
    @patch('modules.logging.logging_config.logging.FileHandler')
    def test_setup_logging(self, mock_file_handler, mock_mkdir):
        # Resetear logger para asegurar estado limpio
        logger = logging.getLogger("test-logger")
        logger.handlers = []

        log = setup_logging("test-logger")

        # Nombre correcto
        self.assertEqual(log.name, "test-logger")

        # Debe tener al menos un handler (StreamHandler)
        self.assertGreaterEqual(len(log.handlers), 1)

        # Logger debe propagar
        self.assertTrue(log.propagate)


if __name__ == '__main__':
    unittest.main()
