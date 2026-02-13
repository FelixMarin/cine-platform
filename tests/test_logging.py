import unittest
import logging
import sys
import os
from unittest.mock import patch
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.logging.logging_config import setup_logging


class TestLogging(unittest.TestCase):

    @patch('modules.logging.logging_config.Path.mkdir')
    @patch('modules.logging.logging_config.logging.FileHandler')
    def test_setup_logging(self, mock_file_handler, mock_mkdir):

        # Limpiar root logger
        root = logging.getLogger()
        for h in root.handlers[:]:
            root.removeHandler(h)

        # Limpiar logger específico
        logger = logging.getLogger("test-logger")
        for h in logger.handlers[:]:
            logger.removeHandler(h)

        log = setup_logging("test-logger")

        self.assertEqual(log.name, "test-logger")
        self.assertGreaterEqual(len(log.handlers), 1)
        self.assertTrue(log.propagate)


if __name__ == '__main__':
    unittest.main()
