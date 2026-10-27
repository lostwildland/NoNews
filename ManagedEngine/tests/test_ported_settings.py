import importlib.util
from pathlib import Path
import sqlite3
import unittest


class SettingsTest(unittest.TestCase):
    def test_processors_round_trip_and_invalid_write(self):
        spec = importlib.util.spec_from_file_location('io_settings', Path(__file__).resolve().parents[1] / 'io_port/settings.py')
        settings = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(settings)
        db = sqlite3.connect(':memory:')
        settings.ensure_schema(db)
        self.assertEqual(settings.processors(db, fallback=1), 1)
        settings.save_processors(db, 3, at='2026-01-01T00:00:00Z')
        self.assertEqual(settings.processors(db), 3)
        with self.assertRaises(ValueError):
            settings.save_processors(db, 0, at='2026-01-01T00:00:01Z')
        self.assertEqual(settings.processors(db), 3)


if __name__ == '__main__':
    unittest.main()
